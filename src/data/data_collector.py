import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirQualityDataCollector:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://api.openaq.org/v3"
        self.api_key = os.getenv('OPENAQ_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAQ API key not found. Please set OPENAQ_API_KEY in .env file")
        
        # Log first few characters of API key for debugging (safely)
        logger.info(f"Using API key starting with: {self.api_key[:8]}...")
        
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'AirQualityDataCollector/1.0',
            'X-API-Key': self.api_key  # Correct header for OpenAQ v3
        }

    def get_locations(self, city, country="US", limit=10):
        """
        List available locations for a city and country using OpenAQ v3 API.
        Returns a list of location dicts.
        """
        url = f"{self.base_url}/locations"
        params = {
            'city': city,
            'country': country,
            'limit': limit
        }
        try:
            # Log the request details for debugging
            logger.info(f"Making request to: {url}")
            logger.info(f"With params: {params}")
            logger.info(f"Using headers: {self.headers}")
            
            response = requests.get(url, params=params, headers=self.headers)
            
            # Log response details for debugging
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            data = response.json()
            locations = data.get('results', [])
            if not locations:
                logger.warning(f"No locations found for {city}, {country}")
            else:
                logger.info(f"Found {len(locations)} locations for {city}, {country}")
            return locations
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching locations for {city}, {country}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            return []

    def fetch_air_quality_data(self, location_id, start_date, end_date, parameters=None, max_pages=10):
        """
        Fetch air quality data from OpenAQ API v3 for a specific location_id and date range.
        Args:
            location_id (int): OpenAQ location ID
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            parameters (list): List of parameters to fetch (e.g., ['pm25', 'pm10', 'o3'])
            max_pages (int): Maximum number of pages to fetch per parameter
        Returns:
            pd.DataFrame: DataFrame containing the air quality data
        """
        if parameters is None:
            parameters = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']

        all_data = []
        for parameter in parameters:
            page = 1
            total_results = 0
            while page <= max_pages:
                try:
                    url = f"{self.base_url}/measurements"
                    params = {
                        'location_id': location_id,
                        'parameter': parameter,
                        'date_from': start_date,
                        'date_to': end_date,
                        'limit': 100,
                        'page': page
                    }
                    response = requests.get(url, params=params, headers=self.headers)
                    response.raise_for_status()
                    data = response.json()
                    results = data.get('results', [])
                    if not results:
                        break
                    df = pd.DataFrame(results)
                    if not df.empty:
                        df['parameter'] = parameter  # Ensure parameter column exists
                        all_data.append(df)
                        total_results += len(df)
                        logger.info(f"Fetched {len(df)} records for {parameter} in location {location_id} (page {page})")
                    if len(results) < 100:
                        break  # Last page
                    page += 1
                    time.sleep(0.2)  # Be nice to the API
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching {parameter} data for location {location_id} on page {page}: {str(e)}")
                    if hasattr(e.response, 'text'):
                        logger.error(f"Response text: {e.response.text}")
                    break
            if total_results == 0:
                logger.warning(f"No data found for {parameter} in location {location_id}")

        if not all_data:
            return pd.DataFrame()

        combined_df = pd.concat(all_data, ignore_index=True)
        processed_df = self._process_data(combined_df)
        return processed_df

    def _process_data(self, df):
        if df.empty:
            return df
        # Extract relevant columns for v3
        processed_df = df[['date', 'parameter', 'value', 'unit', 'location', 'city', 'country']].copy()
        # Convert date to datetime
        processed_df['date'] = pd.to_datetime(processed_df['date'].apply(lambda x: x['utc'] if isinstance(x, dict) and 'utc' in x else x))
        # Pivot the data to have parameters as columns
        processed_df = processed_df.pivot_table(
            index=['date', 'location', 'city', 'country'],
            columns='parameter',
            values='value',
            aggfunc='mean'
        ).reset_index()
        return processed_df

def main():
    try:
        collector = AirQualityDataCollector()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        cities = ['Los Angeles', 'New York', 'Chicago']
        country = 'US'
        for city in cities:
            logger.info(f"Looking up locations for {city}, {country}")
            locations = collector.get_locations(city, country=country, limit=3)
            if not locations:
                logger.warning(f"No locations found for {city}, skipping.")
                continue
            for loc in locations:
                location_id = loc['id']
                location_name = loc['name']
                logger.info(f"Fetching data for {city} - {location_name} (ID: {location_id})")
                df = collector.fetch_air_quality_data(
                    location_id=location_id,
                    start_date=start_date_str,
                    end_date=end_date_str
                )
                if not df.empty:
                    output_dir = 'data/raw'
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{output_dir}/{city.lower().replace(' ', '_')}_{location_name.lower().replace(' ', '_')}_air_quality.csv"
                    df.to_csv(filename, index=False)
                    logger.info(f"Saved data for {city} - {location_name} to {filename}")
                else:
                    logger.warning(f"No data collected for {city} - {location_name}")
    except ValueError as e:
        logger.error(str(e))
        logger.error("Please set your OpenAQ API key in the .env file")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main() 