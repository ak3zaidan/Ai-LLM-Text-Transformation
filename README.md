
**Deploy with**

gcloud functions deploy jig \
  --gen2 \
  --runtime=python310 \
  --entry-point=main \
  --region=us-central1 \
  --trigger-http \
  --allow-unauthenticated

