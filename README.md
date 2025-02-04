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

The script `update_dockerfiles_to_new_release.py` takes care of step 1. and 2. above.
The script `docker_build_from_latest_tag.py` takes care of step 3. and 4.
above.

Usage
-----

* Enter new Debian release date in `update_dockerfiles_to_new_release.py` and
  run the script.

    ```sh
    poetry run python update_dockerfiles_to_new_release.py
    ```

* Run the script `docker_build_from_latest_tag.py`.

    ```sh
    poetry run python docker_build_from_latest_tag.py
    ```

Experimental updates
--------------------

The scripts can also be used to update and rebuild the images locally, without
pushing to GitHub or Docker Hub. This is achieved by setting the `push=False`
argument in the `update_dockerfiles_to_new_release.py` script, and by not
providing GitHub or Docker Hub access tokens in the
`docker_build_from_latest_tag.py` script.
