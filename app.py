
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

    def fetch_events(self, days=30):
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
            # Apply filters
            if start_date and event['geometry'][0]['date'][:10] < start_date:
                continue
            if end_date and event['geometry'][0]['date'][:10] > end_date:
                continue
            if event_type and event['categories'][0]['id'] != event_type:
                continue
            
            magnitude = event.get('magnitudeValue')
            if magnitude:
                magnitude = float(magnitude)
                if min_magnitude and magnitude < float(min_magnitude):
                    continue
                if max_magnitude and magnitude > float(max_magnitude):
                    continue
            
            filtered_events.append(event)

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
        if not self.events_cache:
            return {
                'event_count': 0,
                'categories': {},
                'magnitudes': {'low': 0, 'medium': 0, 'high': 0},
                'daily_counts': {}
            }

        stats = {
            'event_count': len(self.events_cache['events']),
            'categories': {},
            'magnitudes': {'low': 0, 'medium': 0, 'high': 0},
            'daily_counts': {}
        }

        for event in self.events_cache['events']:
            # Category statistics
            category = event['categories'][0]['title']
            stats['categories'][category] = stats['categories'].get(category, 0) + 1

            # Magnitude statistics
            if 'magnitudeValue' in event:
                magnitude = float(event['magnitudeValue'])
                if magnitude < 3:
                    stats['magnitudes']['low'] += 1
                elif magnitude < 6:
                    stats['magnitudes']['medium'] += 1
                else:
                    stats['magnitudes']['high'] += 1

            # Daily counts
            date = event['geometry'][0]['date'][:10]
            stats['daily_counts'][date] = stats['daily_counts'].get(date, 0) + 1

        return stats

    def get_trend_analysis(self, category=None, period='monthly'):
        """Analyze trends in event frequency"""
        events = self.get_filtered_events(event_type=category)
        
        # Group events by period
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

        # Calculate trends
        counts = list(periods.values())
        if len(counts) > 1:
            trend = (counts[-1] - counts[0]) / len(counts)
        else:
            trend = 0

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

#ANALYSIS
def get_analysis_data(self, period=30):
    """Get analysis data from cached events"""
    events = self.get_filtered_events()
    
    # Initialize analysis containers
    timeline_data = {}
    category_data = {}
    geographic_data = {}
    severity_data = []

    for event in events.get('events', []):
        # Get event date
        date = event['geometry'][0]['date'][:10]
        timeline_data[date] = timeline_data.get(date, 0) + 1
        
        # Get category
        category = event['categories'][0]['title']
        category_data[category] = category_data.get(category, 0) + 1
        
        # Get geographic region
        if event['geometry']:
            coords = event['geometry'][0]['coordinates']
            lat = coords[1]
            region = self.get_region_name(lat)
            geographic_data[region] = geographic_data.get(region, 0) + 1
        
        # Get severity if available
        if 'magnitudeValue' in event:
            severity_data.append({
                'date': date,
                'value': float(event['magnitudeValue']),
                'category': category
            })

    return {
        'trends': {
            'labels': sorted(timeline_data.keys()),
            'values': [timeline_data[k] for k in sorted(timeline_data.keys())]
        },
        'categories': {
            'labels': list(category_data.keys()),
            'values': list(category_data.values())
        },
        'geographic': geographic_data,
        'severity': {
            'labels': [d['date'] for d in severity_data],
            'values': [d['value'] for d in severity_data],
            'categories': [d['category'] for d in severity_data]
        }
    }

def get_region_name(self, lat):
    """Get region name based on latitude"""
    if lat > 66.5: return 'Arctic'
    elif lat > 23.5: return 'Northern Hemisphere'
    elif lat > 0: return 'Tropics (North)'
    elif lat > -23.5: return 'Tropics (South)'
    elif lat > -66.5: return 'Southern Hemisphere'
    else: return 'Antarctic'

# Add these new routes to your existing Flask app
@app.route('/analysis')
def analysis():
    """Analysis dashboard route"""
    return render_template('analysis.html')

@app.route('/api/analysis/data')
def get_analysis_data():
    """Get all analysis data"""
    period = request.args.get('period', '30')
    data = eonet_data.get_analysis_data(period=int(period))
    return jsonify(data)
if __name__ == '__main__':
    app.run(debug=True)
