# Raspberry Pi Image with KStars (Automated Build)

This project uses [pi-gen](https://github.com/RPi-Distro/pi-gen) to build a custom Raspberry Pi OS image with KStars pre-installed.

## How it works
- The GitHub Actions workflow in `.github/workflows/build-pi-image.yml` clones pi-gen and adds a custom stage to install KStars.
- The workflow builds the image using Docker and uploads the result as an artifact.

## Customizing the build
- To add more packages or customizations, edit the script in `stage2/04-kstars/00-install-kstars` within the workflow.
- For advanced customizations, refer to the [pi-gen documentation](https://github.com/RPi-Distro/pi-gen/blob/main/README.md).

## Manual build (optional)
If you want to build locally:

```sh
git clone https://github.com/RPi-Distro/pi-gen.git
cd pi-gen
mkdir -p stage2/04-kstars
echo -e '#!/bin/bash\nset -e\napt-get update\napt-get install -y kstars' > stage2/04-kstars/00-install-kstars
chmod +x stage2/04-kstars/00-install-kstars
sudo ./build-docker.sh
```

The final image will be in the `deploy/` directory.
# scope-pi
A raspberry pi image builder that include kstars/ekos and citrascope
