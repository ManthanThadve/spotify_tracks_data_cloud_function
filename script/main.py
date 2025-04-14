"""Spotify tracks fetcher and publisher Cloud Function."""

import functions_framework
import json
import os
from google.cloud import logging as cloud_logging
from google.cloud import pubsub_v1
from google.cloud import storage
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Initialize Cloud Logging client
logging_client = cloud_logging.Client()
logger = logging_client.logger('spotify_tracks_function')


def read_config_from_gcs():
    """Read configuration from GCS bucket.
    
    Returns:
        dict: Configuration data loaded from GCS
        
    Raises:
        ValueError: If required environment variables are not set
        Exception: For any other errors reading from GCS
    """
    try:
        bucket_name = os.environ.get('CONFIG_BUCKET_NAME')
        config_file_path = os.environ.get('CONFIG_FILE_PATH')
        # bucket_name = 'configuration_store'
        # config_file_path = 'Cloud_Function_Config/spotify_tracks_publisher/configuration.json'

        if not bucket_name or not config_file_path:
            raise ValueError("CONFIG_BUCKET_NAME and CONFIG_FILE_PATH environment variables must be set")
            
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(config_file_path)
        config_data = json.loads(blob.download_as_string())
        return config_data
    except Exception as e:
        logger.log_text(f"Error reading config from GCS: {str(e)}", severity="ERROR")
        raise


def publish_track_to_pubsub(track, publisher, topic_path):
    """Publish a single track to Pub/Sub.
    
    Args:
        track (dict): Track data to publish
        publisher: Pub/Sub publisher client
        topic_path (str): Full path of Pub/Sub topic
        
    Returns:
        str: Message ID of published message
    """
    message_data = json.dumps(track).encode("utf-8")
    track_name = track.get('name', 'Unknown Track')
    
    logger.log_text(f"Publishing track '{track_name}' to Pub/Sub", severity="INFO")
    future = publisher.publish(topic_path, data=message_data)
    publish_result = future.result()  # Wait for confirmation
    
    logger.log_text(f"Successfully published message with ID: {publish_result}", severity="INFO")
    return publish_result


def fetch_spotify_tracks(spotify_client):
    """Fetch tracks from Spotify API.
    
    Args:
        spotify_client: Initialized Spotify client
        
    Returns:
        list: List of track items from Spotify
        
    Raises:
        ValueError: If no valid track data is found in response
    """
    batch_size = config['spotify'].get('batch_size', 50)  # Default to 50 if not specified
    results = spotify_client.search(q="track:recent", type="track", limit=batch_size)
    
    logger.log_struct({
        'message': 'Received results from Spotify API',
        'results': results
    }, severity="DEBUG")
    
    if not (results and "tracks" in results and "items" in results["tracks"]):
        raise ValueError("No tracks data found in Spotify API response")
        
    return results["tracks"]["items"]


# Load configuration from GCS
config = read_config_from_gcs()
SPOTIFY_CLIENT_ID = config['spotify']['client_id']
SPOTIFY_CLIENT_SECRET = config['spotify']['client_secret']
PUBSUB_TOPIC_PATH = config['pubsub']['topic_path']

# Initialize clients
spotify_client = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
)
publisher = pubsub_v1.PublisherClient()


@functions_framework.http
def fetch_and_publish_spotify_tracks(request):
    """HTTP Cloud Function to fetch Spotify tracks and publish to Pub/Sub.
    
    Args:
        request: HTTP request object
        
    Returns:
        tuple: Response dict and HTTP status code
        
    Raises:
        ValueError: For validation errors
        Exception: For any other errors
    """
    try:
        logger.log_text("Starting to fetch Spotify tracks", severity="INFO")
        
        # Fetch tracks from Spotify
        tracks_data = fetch_spotify_tracks(spotify_client)
        logger.log_text(
            f"Successfully retrieved {len(tracks_data)} tracks from Spotify",
            severity="INFO"
        )

        # Publish tracks to Pub/Sub
        message_ids = []
        for track in tracks_data:
            message_id = publish_track_to_pubsub(track, publisher, PUBSUB_TOPIC_PATH)
            message_ids.append(message_id)

        publish_result = ",".join(message_ids)
        logger.log_text("All tracks published successfully", severity="INFO")
        
        return {"status": "success", "message_id": str(publish_result)}, 200

    except ValueError as e:
        logger.log_text(str(e), severity="ERROR")
        return {"status": "error", "message": str(e)}, 500
        
    except Exception as e:
        logger.log_text(
            f"Error occurred while processing tracks: {str(e)}",
            severity="ERROR"
        )
        logger.log_struct({
            'message': 'Function execution failed',
            'error': str(e),
            'traceback': str(e.__traceback__)
        }, severity="ERROR")
        return {"status": "error", "message": str(e)}, 500


if __name__ == "__main__":
    # For local testing
    request = None  # Simulate HTTP request
    fetch_and_publish_spotify_tracks(request)