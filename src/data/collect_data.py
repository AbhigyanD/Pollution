import os
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

def get_nyc_stations():
    """Get list of EPA monitoring stations in NYC"""
    # These are the main EPA monitoring stations in NYC
    stations = {
        '36-005-0112': {'name': 'IS 52 - Bronx', 'lat': 40.813, 'lon': -73.913},
        '36-081-0124': {'name': 'PS 19 - Queens', 'lat': 40.743, 'lon': -73.891},
        '36-047-0010': {'name': 'PS 274 - Brooklyn', 'lat': 40.621, 'lon': -73.912},
        '36-061-0014': {'name': 'CCNY - Manhattan', 'lat': 40.819, 'lon': -73.949}
    }
    return stations

def fetch_epa_data():
    """Fetch data from EPA's AQS for NYC"""
    # Using EPA's AQS API endpoint
    base_url = "https://aqs.epa.gov/data/api/dailyData/byState"
    
    # Parameters for the API request
    params = {
        'email': 'test@example.com',  # EPA requires an email for API access
        'key': 'test',  # EPA requires a key, but 'test' works for public data
        'param': '42101,42401,42602,44201,88101',  # PM2.5, CO, NO2, O3, PM10
        'bdate': (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
        'edate': datetime.now().strftime('%Y%m%d'),
        'state': '36'  # New York state FIPS code
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception fetching data: {str(e)}")
        return None

def main():
    # Create data directory if it doesn't exist
    os.makedirs('data/raw', exist_ok=True)
    
    # Get NYC stations
    print("Getting NYC monitoring stations...")
    stations = get_nyc_stations()
    print(f"Found {len(stations)} stations in NYC")
    
    # Fetch EPA data
    print("\nFetching EPA air quality data...")
    data = fetch_epa_data()
    
    if data and 'Data' in data:
        # Convert to DataFrame
        df = pd.DataFrame(data['Data'])
        
        # Filter for NYC stations
        df = df[df['site_number'].isin(stations.keys())]
        
        # Add station names
        station_names = {k: v['name'] for k, v in stations.items()}
        df['station_name'] = df['site_number'].map(station_names)
        
        # Save raw data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'data/raw/nyc_air_quality_{timestamp}.csv'
        df.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")
        
        # Print summary statistics
        print("\nSummary of collected data:")
        print(f"Total measurements: {len(df)}")
        print("\nParameters available:")
        print(df['parameter_name'].value_counts())
        print("\nStations covered:")
        print(df['station_name'].value_counts())
    else:
        print("No measurements were collected")

if __name__ == "__main__":
    main() 