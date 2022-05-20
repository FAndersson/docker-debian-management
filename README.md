Management of private Docker repos and images
=============================================

Introduction
------------

All my private Docker images are based on Debian stable and Debian testing.
When a new Debian version is released we want to update all of the images by:

1. Update base version for images directly derived from Debian.
    * Update base version for images derived from one of my base images.
2. Tag new image versions.
3. Rebuild images from the latest tag.
4. Push new images to Docker Hub.

The script `update_images_to_new_release.py` takes care of step 1. and 2. above.
The script `docker_build_from_latest_github_tag.py` takes care of step 3. and 4.
above.

Usage
-----

* Enter new Debian release date in `update_images_to_new_release.py` and run the
  script. Working directory need to be the parent folder to all Docker
  repositories.
* Enter GitHub access token and Docker Hub access token in
  `docker_build_from_latest_github_tag.py` and run the script.
