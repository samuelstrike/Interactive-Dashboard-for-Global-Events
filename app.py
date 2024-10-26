from flask import Flask, render_template, jsonify, request
import requests
import folium
from folium import plugins
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import branca.colormap as cm
from threading import Lock
import time

app = Flask(__name__)


class EONETData:
    def __init__(self):
        self.EONET_API = "https://eonet.gsfc.nasa.gov/api/v3"
        self.events_cache = None
        self.categories_cache = None
        self.last_update = None
        self.update_interval = 300  # 5 minutes
        self.data_lock = Lock()
        self.initialized = False

        # Initialize colormap for events
        self.colormap = cm.LinearColormap(
            colors=['#FFEB3B', '#FF9800', '#F44336'],
            vmin=0, vmax=10,
            caption='Event Magnitude'
        )

        # Initialize data
        self.initialize()

    def initialize(self):
        """Initialize data"""
        print("Starting initial data load...")
        try:
            self.fetch_categories()
            self.fetch_events()
            self.initialized = True
            print("Initial data load completed successfully")
            return True
        except Exception as e:
            print(f"Error during initial data load: {e}")
            return False

    def fetch_events(self, days=365):
        """Fetch events from EONET API"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            params = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'status': 'all'
            }

            response = requests.get(f"{self.EONET_API}/events", params=params)
            response.raise_for_status()

            with self.data_lock:
                self.events_cache = response.json()
                self.last_update = datetime.now()

            return True
        except Exception as e:
            print(f"Error fetching events: {e}")
            return False

    def fetch_categories(self):
        """Fetch categories from EONET API"""
        try:
            response = requests.get(f"{self.EONET_API}/categories")
            response.raise_for_status()
            self.categories_cache = response.json()
            return True
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return False

    def get_filtered_events(self, start_date=None, end_date=None, event_type=None,
                            min_magnitude=None, max_magnitude=None):
        """Get filtered events based on criteria"""
        if not self.events_cache:
            return {"events": []}

        filtered_events = []
        for event in self.events_cache.get('events', []):
            try:
                # Apply date and type filters
                if start_date and event['geometry'][0]['date'][:10] < start_date:
                    continue
                if end_date and event['geometry'][0]['date'][:10] > end_date:
                    continue
                if event_type and event['categories'][0]['id'] != event_type:
                    continue

                # Initialize magnitude as None
                magnitude = None

                # Try to get magnitude from event root
                if 'magnitudeValue' in event:
                    try:
                        mag_value = event.get('magnitudeValue')
                        if mag_value is not None and str(mag_value).strip():
                            magnitude = float(mag_value)
                    except (ValueError, TypeError):
                        pass

                # Try to get magnitude from geometry if not found in root
                if magnitude is None and event.get('geometry'):
                    for geo in event['geometry']:
                        try:
                            mag_value = geo.get('magnitudeValue')
                            if mag_value is not None and str(mag_value).strip():
                                magnitude = float(mag_value)
                                break
                        except (ValueError, TypeError):
                            continue

                # Apply magnitude filters if magnitude exists
                if magnitude is not None and (min_magnitude is not None or max_magnitude is not None):
                    if min_magnitude and magnitude < float(min_magnitude):
                        continue
                    if max_magnitude and magnitude > float(max_magnitude):
                        continue

                filtered_events.append(event)

            except Exception as e:
                print(f"Error filtering event: {str(e)}")
                continue

        return {"events": filtered_events}

    def create_map(self, events):
        """Create enhanced Folium map with events"""
        m = folium.Map(
            location=[20, 0],
            zoom_start=3,
            tiles='CartoDB positron',
            prefer_canvas=True
        )

        # Create feature groups for different event types
        event_groups = {}

        for event in events.get('events', []):
            if event.get('geometry') and event['geometry'][0].get('coordinates'):
                coords = event['geometry'][0]['coordinates']
                category = event['categories'][0]['title']
                magnitude = event.get('magnitudeValue', 0)

                if magnitude:
                    magnitude = float(magnitude)

                # Determine icon and color based on category and magnitude
                icon_color = self.get_magnitude_color(magnitude)
                icon = self.get_category_icon(category)

                # Create feature group for category if not exists
                if category not in event_groups:
                    event_groups[category] = folium.FeatureGroup(name=category)

                # Create popup content
                popup_content = f"""
                    <div style="width: 300px">
                        <h4>{event['title']}</h4>
                        <p><b>Category:</b> {category}</p>
                        <p><b>Date:</b> {event['geometry'][0]['date'][:10]}</p>
                        {'<p><b>Magnitude:</b> ' + str(magnitude) + '</p>' if magnitude else ''}
                        <p><b>Description:</b> {event.get('description', 'No description available')}</p>
                    </div>
                """

                # Add marker
                folium.CircleMarker(
                    location=[coords[1], coords[0]],
                    radius=8,
                    popup=folium.Popup(popup_content, max_width=300),
                    color='black',
                    weight=1,
                    fill=True,
                    fill_color=icon_color,
                    fill_opacity=0.7,
                    tooltip=f"{category}: {event['title']}"
                ).add_to(event_groups[category])

        # Add all feature groups to map
        for group in event_groups.values():
            group.add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add fullscreen option
        plugins.Fullscreen().add_to(m)

        return m._repr_html_()

    def get_magnitude_color(self, magnitude):
        """Determine color based on magnitude"""
        if not magnitude:
            return '#3388ff'  # Default blue
        if magnitude < 3:
            return '#FFEB3B'  # Yellow
        if magnitude < 6:
            return '#FF9800'  # Orange
        return '#F44336'  # Red

    def get_category_icon(self, category):
        """Get appropriate icon for category"""
        icons = {
            'Wildfires': 'fire',
            'Volcanoes': 'mountain',
            'Severe Storms': 'bolt',
            'Floods': 'water',
            'Earthquakes': 'globe',
            'Drought': 'sun',
            'Landslides': 'mountain',
            'Sea and Lake Ice': 'snowflake',
            'Temperature Extremes': 'thermometer'
        }
        return icons.get(category, 'info-circle')

    def get_summary_statistics(self):
        """Generate summary statistics"""
        stats = {
            'event_count': 0,
            'categories': {},
            'magnitudes': {
                'low': 0,  # 0-1.5
                'medium': 0,  # 1.5-5
                'high': 0  # 5+
            },
            'daily_counts': {}
        }

        if not self.events_cache:
            return stats

        stats['event_count'] = len(self.events_cache['events'])

        for event in self.events_cache['events']:
            try:
                # Category statistics
                category = event['categories'][0]['title']
                stats['categories'][category] = stats['categories'].get(category, 0) + 1

                # Daily counts
                date = event['geometry'][0]['date'][:10]
                stats['daily_counts'][date] = stats['daily_counts'].get(date, 0) + 1

                # Magnitude statistics
                magnitude = None
                mag_id = None

                if 'magnitudeValue' in event and 'magnitudeUnit' in event:
                    magnitude = float(event['magnitudeValue'])
                    mag_id = event.get('magnitudeUnit')
                elif event.get('geometry', []):
                    for geo in event['geometry']:
                        if 'magnitudeValue' in geo and 'magnitudeUnit' in geo:
                            magnitude = float(geo['magnitudeValue'])
                            mag_id = geo.get('magnitudeUnit')
                            break

                if magnitude is not None:
                    if magnitude < 1.5:
                        stats['magnitudes']['low'] += 1
                    elif magnitude < 5.0:
                        stats['magnitudes']['medium'] += 1
                    else:
                        stats['magnitudes']['high'] += 1
                else:
                    stats['magnitudes']['low'] += 1

            except Exception as e:
                print(f"Error processing event: {e}")
                continue

        return stats

    def get_trend_analysis(self, category=None, period='monthly'):
        """Analyze trends in event frequency"""
        events = self.get_filtered_events(event_type=category)

        periods = {}
        for event in events['events']:
            date = datetime.strptime(event['geometry'][0]['date'][:10], '%Y-%m-%d')
            if period == 'monthly':
                key = date.strftime('%Y-%m')
            elif period == 'weekly':
                key = date.strftime('%Y-W%W')
            else:
                key = date.strftime('%Y-%m-%d')

            periods[key] = periods.get(key, 0) + 1

        counts = list(periods.values())
        trend = (counts[-1] - counts[0]) / len(counts) if len(counts) > 1 else 0

        return {
            'periods': list(periods.keys()),
            'counts': counts,
            'trend': trend,
            'average': sum(counts) / len(counts) if counts else 0,
            'max': max(counts) if counts else 0,
            'min': min(counts) if counts else 0
        }


# Initialize EONET data handler
eonet_data = EONETData()


@app.route('/')
def index():
    """Main dashboard route"""
    events = eonet_data.get_filtered_events()
    map_html = eonet_data.create_map(events)
    return render_template('index.html', map_html=map_html)


@app.route('/trends')
def trends():
    """Trends analysis route"""
    return render_template('trends.html')


@app.route('/analysis')
def analysis():
    """New analysis dashboard route"""
    return render_template('analysis.html')


@app.route('/api/events')
def get_events():
    """API endpoint for events"""
    params = {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'event_type': request.args.get('event_type'),
        'min_magnitude': request.args.get('min_magnitude'),
        'max_magnitude': request.args.get('max_magnitude')
    }
    return jsonify(eonet_data.get_filtered_events(**params))


@app.route('/api/map')
def get_map():
    """API endpoint for map"""
    params = {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'event_type': request.args.get('event_type'),
        'min_magnitude': request.args.get('min_magnitude'),
        'max_magnitude': request.args.get('max_magnitude')
    }
    events = eonet_data.get_filtered_events(**params)
    return eonet_data.create_map(events)


@app.route('/api/summary')
def get_summary():
    """API endpoint for summary statistics"""
    return jsonify(eonet_data.get_summary_statistics())


@app.route('/api/categories')
def get_categories():
    """API endpoint for categories"""
    return jsonify(eonet_data.categories_cache or {'categories': []})


@app.route('/api/trends')
def get_trends():
    """API endpoint for trend analysis"""
    category = request.args.get('category')
    period = request.args.get('period', 'monthly')
    return jsonify(eonet_data.get_trend_analysis(category, period))


@app.route('/api/analysis/geographic')
def get_geographic_data():
    """Get geographic distribution data from EONET"""
    events = eonet_data.get_filtered_events()
    geographic_data = []

    regions = {
        'Antarctic': 0,
        'Arctic': 0,
        'Northern Hemisphere': 0,
        'Southern Hemisphere': 0,
        'Tropics (North)': 0,
        'Tropics (South)': 0
    }

    for event in events.get('events', []):
        if event.get('geometry') and event['geometry'][0].get('coordinates'):
            lat = event['geometry'][0]['coordinates'][1]
            region = get_region_name(lat)
            regions[region] += 1

    for region, count in regions.items():
        geographic_data.append({
            'region': region,
            'events': count
        })

    return jsonify(geographic_data)


@app.route('/api/analysis/daily')
def get_daily_events():
    """Get daily events data for the last week"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    events = eonet_data.get_filtered_events(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    daily_data = []
    current = start_date
    date_counts = {}

    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        date_counts[date_str] = 0
        current += timedelta(days=1)

    for event in events.get('events', []):
        date = event['geometry'][0]['date'][:10]
        if date in date_counts:
            date_counts[date] += 1

    for date, count in sorted(date_counts.items()):
        daily_data.append({
            'date': date,
            'events': count
        })

    return jsonify(daily_data)


def get_region_name(lat):
    """Helper function to determine region based on latitude"""
    if lat > 66.5:
        return 'Arctic'
    elif lat > 23.5:
        return 'Northern Hemisphere'
    elif lat > 0:
        return 'Tropics (North)'
    elif lat > -23.5:
        return 'Tropics (South)'
    elif lat > -66.5:
        return 'Southern Hemisphere'
    else:
        return 'Antarctic'


@app.route('/api/analysis/data')
def get_analysis_data():
    """Get all analysis data"""
    period = request.args.get('period', '30')

    # Get events for the specified period
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=int(period))

    events = eonet_data.get_filtered_events(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    # Process data for timeline
    timeline_data = {}
    current = start_date
    while current <= end_date:
        timeline_data[current.strftime('%Y-%m-%d')] = 0
        current += timedelta(days=1)

    # Initialize data containers
    category_data = {}
    geographic_data = {}
    severity_data = {
        'labels': [],
        'values': [],
        'categories': []
    }

    # Process each event
    for event in events.get('events', []):
        # Timeline data
        date = event['geometry'][0]['date'][:10]
        if date in timeline_data:
            timeline_data[date] += 1

        # Category data
        category = event['categories'][0]['title']
        category_data[category] = category_data.get(category, 0) + 1

        # Geographic data
        if event.get('geometry') and event['geometry'][0].get('coordinates'):
            lat = event['geometry'][0]['coordinates'][1]
            region = get_region_name(lat)
            geographic_data[region] = geographic_data.get(region, 0) + 1

        # Severity data
        if 'magnitudeValue' in event:
            severity_data['labels'].append(date)
            severity_data['values'].append(float(event['magnitudeValue']))
            severity_data['categories'].append(category)

    return jsonify({
        'trends': {
            'labels': list(timeline_data.keys()),
            'values': list(timeline_data.values())
        },
        'categories': {
            'labels': list(category_data.keys()),
            'values': list(category_data.values())
        },
        'geographic': geographic_data,
        'severity': severity_data
    })


@app.route('/api/analysis/correlation')
def get_correlation_data():
    """Get correlation data for numeric features"""
    events = eonet_data.get_filtered_events()

    # Create a list to store the processed data
    data_list = []

    # Create a category to numeric mapping
    category_mapping = {}
    category_counter = 0

    for event in events.get('events', []):
        date = datetime.strptime(event['geometry'][0]['date'][:10], '%Y-%m-%d')
        coordinates = event['geometry'][0]['coordinates']
        category = event['categories'][0]['id']

        # Map category to numeric value if not already mapped
        if category not in category_mapping:
            category_mapping[category] = category_counter
            category_counter += 1

        data_list.append({
            'latitude': coordinates[1],
            'longitude': coordinates[0],
            'month': date.month,
            'day': date.day,
            'day_of_week': date.weekday(),
            'is_weekend': 1 if date.weekday() >= 5 else 0,
            'category_code': category_mapping[category]
        })

    # Convert to DataFrame
    df = pd.DataFrame(data_list)

    # Calculate correlations only for numeric columns
    correlations = df.select_dtypes(include=[np.number]).corr(method='pearson')

    # Convert to the format needed for the heatmap
    correlation_data = {
        'labels': correlations.columns.tolist(),
        'values': correlations.values.tolist()
    }

    return jsonify(correlation_data)

if __name__ == '__main__':
    app.run(debug=True)
