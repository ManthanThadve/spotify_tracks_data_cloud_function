# Spotify Tracks Fetcher and Publisher Cloud Function

This Cloud Function fetches recent tracks from the Spotify API and publishes them to a Google Cloud Pub/Sub topic.

## Overview

The function performs the following operations:
1. Reads configuration from Google Cloud Storage
2. Authenticates with the Spotify API using client credentials
3. Fetches recent tracks from Spotify (configurable batch size)
4. Publishes each track to a specified Pub/Sub topic
5. Returns a success response with message IDs

## Configuration

The function uses a configuration file stored in Google Cloud Storage with the following structure:

```json
{
    "spotify": {
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "batch_size": 5
    },
    "pubsub": {
        "topic_path": "projects/your-project-id/topics/your-topic-name"
    }
}
```

- `batch_size`: Controls how many tracks to fetch from Spotify API (maximum: 50)
- `topic_path`: The full path to the Pub/Sub topic where tracks will be published

## Required Permissions

The service account used by the Cloud Function (`your-service-account@your-project-id.iam.gserviceaccount.com`) requires the following permissions:

### Google Cloud Storage
- `storage.objects.get` - To read the configuration file from GCS
- `storage.buckets.get` - To access the configuration bucket

### Google Cloud Pub/Sub
- `pubsub.topics.publish` - To publish messages to the specified topic

### Google Cloud Logging
- `logging.logEntries.create` - To write logs to Cloud Logging

### Cloud Functions
- `cloudfunctions.functions.invoke` - To invoke the function

You can grant these permissions using the following commands:

```bash
# Grant Storage permissions
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Grant Pub/Sub permissions
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

# Grant Logging permissions
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

## Deployment

### Prerequisites

- Google Cloud SDK installed and configured
- Appropriate permissions to deploy Cloud Functions
- Spotify API credentials
- Google Cloud Pub/Sub topic created

### Deployment Command

```bash
gcloud functions deploy fetch_and_publish_spotify_tracks \
  --gen2 \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --region your-region \
  --source . \
  --entry-point fetch_and_publish_spotify_tracks \
  --set-env-vars CONFIG_BUCKET_NAME=your-config-bucket,CONFIG_FILE_PATH=your-config-path/configuration.json \
  --service-account your-service-account@your-project-id.iam.gserviceaccount.com
```

### Environment Variables

- `CONFIG_BUCKET_NAME`: The name of the GCS bucket containing the configuration file
- `CONFIG_FILE_PATH`: The path to the configuration file within the bucket

## Function Response

When the function is successfully triggered, it returns a JSON response with the following structure:

```json
{
  "message_id": "14225494896414287,14225471985146962,14227661286313019,14225373904419398,14224348127560947",
  "status": "success"
}
```

- `message_id`: Comma-separated list of message IDs for each track published to Pub/Sub
- `status`: Indicates the execution status ("success" or "error")

## Error Handling

If an error occurs during execution, the function returns a JSON response with:

```json
{
  "status": "error",
  "message": "Error description"
}
```

## Local Testing

To test the function locally, you can run:

```bash
python main.py
```

This will execute the function with a simulated HTTP request.

## Dependencies

- functions-framework
- google-cloud-logging
- google-cloud-pubsub
- google-cloud-storage
- spotipy