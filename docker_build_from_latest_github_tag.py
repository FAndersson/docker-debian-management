import argparse
import datetime
import subprocess
from typing import Optional

import github


def get_latest_tag(access_token: str, repo_name: str) -> Optional[str]:
    """
    Get latest tag from a GitHub repository.

    :param access_token: Personal access token for the account where the
        repository resides.
    :param repo_name: Name of the repository.
    :return: Tag name, or None if repo doesn't exist or if it has no
        tags.
    """
    # Get GitHub account from access token
    g = github.Github(access_token)
    # Get repo with given name
    try:
        repo = g.get_repo("{}/{}".format(g.get_user().login, repo_name))
    except github.GithubException:
        # Repo doesn't exist
        return None
    # Get all tags in the repo
    tags = repo.get_tags()
    if tags.totalCount == 0:
        # No tags in repo
        return None
    # Get latest tag by sorting tags on commit date

    def commit_date(tag: github.Tag) -> datetime.datetime:
        """
        Get date and time when the commit corresponding to a tag was
        created.

        :param tag: GitHub tag.
        :return: Date and time when the commit was created.
        """
        return datetime.datetime.strptime(
            repo.get_commit(tag.commit.sha).last_modified,
            "%a, %d %b %Y %H:%M:%S %Z")

    latest_tag = max(tags, key=commit_date)
    return latest_tag.name


def build_image_from_tag(github_login: str, repo_name: str, tag: str,
                         docker_login: str) -> Optional[str]:
    """
    Build a Docker image from a tag in a GitHub repository.

    :param github_login: Name of the account where the GitHub repository
        resides.
    :param repo_name: Name of the repository.
    :param tag: Name of the tag to build from.
    :param docker_login: Name of the Docker hub account the image should
        be pushed to.
    :return: Return tag for the new image, or None if the build failed.
    """
    assert repo_name[0:7] == "docker-"
    docker_image = repo_name[7:]
    docker_tag = "{}/{}:{}".format(docker_login, docker_image, tag)
    repo_url = "https://github.com/{}/{}.git".format(github_login, repo_name)
    repo_url_with_tag = repo_url + "#{}".format(tag)
    build_command = [
        "docker",
        "build",
        "--tag",
        docker_tag,
        repo_url_with_tag
    ]
    result = subprocess.run(build_command, capture_output=True)
    if result.returncode != 0:
        print("docker build failed. stdout: {}, stderr: {}"
              .format(result.stdout, result.stderr))
        return None
    return docker_tag


def push_image_to_dockerhub(access_token: str, tag: str) -> bool:
    """
    Push a Docker image to Docker hub.

    :param access_token: Personal access token to the Docker hub account
        the image should be pushed to.
    :param tag: Specification of the image that should be pushed on the
        form 'NAME:TAG'.
    :return: Whether or not the push was successful.
    """
    username_end = tag.find("/")
    assert username_end != -1
    username = tag[0:username_end]
    login_command = [
        "docker",
        "login",
        "--username",
        username,
        "--password",
        access_token
    ]
    result = subprocess.run(login_command, capture_output=True)
    if result.returncode != 0:
        print("docker login failed. stdout: {}, stderr: {}"
              .format(result.stdout, result.stderr))
        return False
    push_command = [
        "docker",
        "push",
        tag
    ]
    result = subprocess.run(push_command, capture_output=True)
    if result.returncode != 0:
        print("docker push failed. stdout: {}, stderr: {}"
              .format(result.stdout, result.stderr))
        return False
    # Also use new image as the new 'latest' version
    image_name_end = tag.find(":")
    assert image_name_end != -1
    image_name = tag[username_end + 1:image_name_end]
    latest_tag = f"{username}/{image_name}:latest"
    tag_command = [
        "docker",
        "tag",
        tag,
        latest_tag
    ]
    result = subprocess.run(tag_command, capture_output=True)
    if result.returncode != 0:
        print("docker tag failed. stdout: {}, stderr: {}"
              .format(result.stdout, result.stderr))
        return False
    push_command = [
        "docker",
        "push",
        latest_tag
    ]
    result = subprocess.run(push_command, capture_output=True)
    if result.returncode != 0:
        print("docker push latest failed. stdout: {}, stderr: {}"
              .format(result.stdout, result.stderr))
        return False
    return True


def build_and_push_tag(github_login: str, github_repo_name: str,
                       github_repo_tag: str, docker_login: str,
                       docker_access_token: str) -> bool:
    """
    Build a Docker image from the Dockerfile in the root of a GitHub
    repository. The version of the repository corresponding to the
    given tag is used. The image is then pushed to Docker hub.

    :param github_login: Name of the account where the GitHub repository
        resides.
    :param github_repo_name: Name of the GitHub repository.
    :param github_repo_tag: Tag defining the version of the GitHub repo
        to use.
    :param docker_login: Name of the Docker hub account the image should
        be pushed to.
    :param docker_access_token: Personal access token to the Docker hub
        account the image should be pushed to.
    :return: Whether or not the image was successfully built and pushed
        to Docker hub.
    """
    image_tag = build_image_from_tag(github_login, github_repo_name,
                                     github_repo_tag, docker_login)
    if image_tag is None:
        return False
    return push_image_to_dockerhub(docker_access_token, image_tag)


def update_fa_repos(github_access_token, docker_access_token):
    """
    Build and push Docker images for my private GitHub repos.

    :param github_access_token: Personal access token to the
        'FAndersson' account.
    :param docker_access_token: Personal access token to the
        'fredrikandersson' account.
    """
    github_login = "FAndersson"
    docker_login = "fredrikandersson"
    repos = [
        "docker-debian-stable-dev-image-base",
        "docker-debian-stable-cpp-image-base",
        "docker-debian-stable-cpp-image-clang",
        "docker-debian-stable-cpp-image-gcc",
        "docker-debian-stable-latex-image",
        "docker-debian-stable-python-image",
        "docker-debian-testing-dev-image-base",
        "docker-debian-testing-cpp-image-base",
        "docker-debian-testing-cpp-image-clang",
        "docker-debian-testing-cpp-image-gcc",
        "docker-debian-testing-python-image",
    ]
    for repo in repos:
        latest_tag = get_latest_tag(github_access_token, repo)
        if latest_tag is None:
            print("Failed to get latest tag in repo {}".format(repo))
            return
        if not build_and_push_tag(github_login, repo, latest_tag, docker_login,
                                  docker_access_token):
            print("Failed to build and push image for repo {}".format(repo))
            return


if __name__ == "__main__":
    # github_access_token = ...
    # docker_access_token = ...
    update_fa_repos(github_access_token, docker_access_token)
