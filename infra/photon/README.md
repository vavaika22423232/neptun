# Photon Geocoder

Photon is the optional local geocoder used by the worker as a fast Ukraine-focused fallback.

Run from this directory:

```bash
./setup_photon_ua.sh
docker compose up -d
```

The import script writes `photon_data/` next to this README. The Docker Compose file mounts that
directory into the Photon container and exposes the service on `127.0.0.1:2322` via Docker port
mapping.
