import datetime
from getpass import getpass
import pathlib
import subprocess
import time
from typing import Optional

from git import Repo, TagReference
import github


def get_latest_github_tag(access_token: str, repo_name: str) -> Optional[str]:
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
        repo = g.get_repo(f"{g.get_user().login}/{repo_name}")
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


def get_latest_local_tag(repo_name: str) -> Optional[str]:
    """
    Get latest tag from a local repository.

    :param repo_name: Name of the repository.
    :return: Tag name, or None if repo doesn't exist or if it has no
        tags.
    """
    repo_path = pathlib.Path(__file__).resolve().parent.parent / repo_name
    git_repo = Repo(repo_path)

    # Get all tags in the repo
    tags = git_repo.tags
    if len(tags) == 0:
        # No tags in repo
        return None
    # Get latest tag by sorting tags on commit date

    def commit_date(tag: TagReference) -> datetime.datetime:
        """
        Get date and time when the commit corresponding to a tag was
        created.

        :param tag: Git tag.
        :return: Date and time when the commit was created.
        """
        return datetime.datetime.fromtimestamp(
            time.mktime(time.gmtime(tag.commit.committed_date)))

    latest_tag = max(tags, key=commit_date)
    return latest_tag


def build_image_from_github_tag(github_login: str, repo_name: str, tag: str,
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
    docker_tag = f"{docker_login}/{docker_image}:{tag}"
    repo_url = f"https://github.com/{github_login}/{repo_name}.git"
    repo_url_with_tag = repo_url + f"#{tag}"
    build_command = [
        "docker",
        "build",
        "--tag",
        docker_tag,
        repo_url_with_tag
    ]
    print("    Build command: " + " ".join(build_command))
    result = subprocess.run(build_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker build failed. stdout: {result.stdout}, stderr: "
              f"{result.stderr}")
        return None
    print(f"Docker image {docker_tag} built from GitHub repo {repo_name}, "
          f"tag {tag}")
    return docker_tag


def build_image_from_local_tag(repo_name: str, tag: str,
                               docker_login: str) -> Optional[str]:
    """
    Build a Docker image from a tag in a local repository.

    :param repo_name: Name of the repository.
    :param tag: Name of the tag to build from.
    :param docker_login: Name of the Docker hub account the image should
        be pushed to.
    :return: Return tag for the new image, or None if the build failed.
    """
    assert repo_name[0:7] == "docker-"
    docker_image = repo_name[7:]
    docker_tag = f"{docker_login}/{docker_image}:{tag}"
    repo_path = pathlib.Path(__file__).resolve().parent.parent / repo_name
    build_command = [
        "docker",
        "build",
        "--tag",
        docker_tag,
        str(repo_path)
    ]
    print("    Build command: " + " ".join(build_command))
    result = subprocess.run(build_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker build failed. stdout: {result.stdout}, stderr: "
              f"{result.stderr}")
        return None
    print(f"Docker image {docker_tag} built from {repo_name}, tag {tag}")
    return docker_tag


def push_image_to_dockerhub(access_token: str, tag: str) -> bool:
    """
    Push a Docker image to Docker hub.

    :param access_token: Personal access token to the Docker hub account
        the image should be pushed to.
    :param tag: Specification of the image that should be pushed on the
        form 'NAME:TAG'.
    :return: Whether the push was successful.
    """
    print("    Docker push")
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
    print(f"    Login command: `{' '.join(login_command[:-1] + ['****'])}`")
    result = subprocess.run(login_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker login failed. stdout: {result.stdout}, stderr: "
              f"{result.stderr}")
        return False
    push_command = [
        "docker",
        "push",
        tag
    ]
    print(f"    Push command: `{' '.join(push_command)}`")
    result = subprocess.run(push_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker push failed. stdout: {result.stdout}, stderr: "
              f"{result.stderr}")
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
    print(f"    Tag command: `{' '.join(tag_command)}`")
    result = subprocess.run(tag_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker tag failed. stdout: {result.stdout}, stderr: "
              f"{result.stderr}")
        return False
    push_command = [
        "docker",
        "push",
        latest_tag
    ]
    print("    Push command: " + " ".join(push_command))
    result = subprocess.run(push_command, capture_output=True)
    if result.returncode != 0:
        print(f"docker push latest failed. stdout: {result.stdout}, "
              f"stderr: {result.stderr}")
        return False
    print(f"Docker image {tag} pushed to Docker hub.")
    return True


def build_and_push_github_tag(
        github_login: str, github_repo_name: str, github_repo_tag: str,
        docker_login: str, docker_access_token: Optional[str]) -> bool:
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
        account the image should be pushed to. Will not push the built
        image to Docker hub if not provided.
    :return: Whether the image was successfully built and optionally
        pushed to Docker hub.
    """
    image_tag = build_image_from_github_tag(
        github_login, github_repo_name, github_repo_tag, docker_login)
    if image_tag is None:
        return False
    if docker_access_token:
        return push_image_to_dockerhub(docker_access_token, image_tag)
    return True


def update_fa_repos(
        github_access_token: Optional[str] = None,
        docker_access_token: Optional[str] = None):
    """
    Build and optionally push Docker images for my private GitHub repos.

    :param github_access_token: Personal access token to the
        'FAndersson' account. Will build from latest tag in GitHub if
        provided. Otherwise build from latest local tag.
    :param docker_access_token: Personal access token to the
        'fredrikandersson' account. Will push the built image to Docker
        hub if provided.
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
        print(f"In repo {repo}")
        if github_access_token:
            latest_tag = get_latest_github_tag(github_access_token, repo)
        else:
            latest_tag = get_latest_local_tag(repo)
        if latest_tag is None:
            print(f"Failed to get latest tag in repo {repo}")
            return
        if github_access_token:
            if not build_and_push_github_tag(
                github_login, repo, latest_tag, docker_login,
                docker_access_token):
                print(f"Failed to build and push image for repo {repo}")
        else:
            if not build_image_from_local_tag(repo, latest_tag, docker_login):
                print(f"Failed to build image for repo {repo}")


if __name__ == "__main__":
    github_access_token = getpass("Enter GitHub access token: ")
    docker_access_token = getpass("Enter Docker access token: ")
    update_fa_repos(github_access_token, docker_access_token)
