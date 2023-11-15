import pathlib
import re
from typing import Optional

from git import Actor, Repo, TagReference


def get_tag(repo: Repo, tag_name: str) -> Optional[TagReference]:
    """
    Get a tag from a repository.

    :param repo: Repository to get tag from.
    :param tag_name: Name of the tag.
    :return: Tag with given name, or None if no such tag exists.
    """
    for tag in repo.tags:
        if tag.name == tag_name:
            return tag
    return None


def update_fa_repos(tag_date: str, folder: pathlib.Path = pathlib.Path(".."),
                    push: bool = False):
    """
    Update private Docker repos to be based on a new version of Debian.

    :param tag_date: Date for the new Debian Docker release, on the form
        '20211011'.
    :param folder: Folder where the Docker repos are located. Absolute
        or relative to this folder.
    :param push: Whether to push changes to GitHub.
    """
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
    tag_date_iso = f"{tag_date[0:4]}-{tag_date[4:6]}-{tag_date[6:8]}"
    commit_messages = {
        "docker-debian-stable-dev-image-base":
            f"Build from {tag_date_iso} version of Debian stable.",
        "docker-debian-stable-cpp-image-base":
            f"Build from {tag_date_iso} version of base dev image.",
        "docker-debian-stable-cpp-image-clang":
            f"Build from {tag_date_iso} version of base cpp image.",
        "docker-debian-stable-cpp-image-gcc":
            f"Build from {tag_date_iso} version of base cpp image.",
        "docker-debian-stable-latex-image":
            f"Build from {tag_date_iso} version of base dev image.",
        "docker-debian-stable-python-image":
            f"Build from {tag_date_iso} version of base dev image.",
        "docker-debian-testing-dev-image-base":
            f"Build from {tag_date_iso} version of Debian testing.",
        "docker-debian-testing-cpp-image-base":
            f"Build from {tag_date_iso} version of base dev image.",
        "docker-debian-testing-cpp-image-clang":
            f"Build from {tag_date_iso} version of base cpp image.",
        "docker-debian-testing-cpp-image-gcc":
            f"Build from {tag_date_iso} version of base cpp image.",
        "docker-debian-testing-python-image":
            f"Build from {tag_date_iso} version of base dev image.",
    }
    tag_messages = {
        "docker-debian-stable-dev-image-base":
            f"From {tag_date_iso} version of Debian stable.",
        "docker-debian-stable-cpp-image-base":
            f"From {tag_date_iso} version of base dev image.",
        "docker-debian-stable-cpp-image-clang":
            f"From {tag_date_iso} version of base cpp image.",
        "docker-debian-stable-cpp-image-gcc":
            f"From {tag_date_iso} version of base cpp image.",
        "docker-debian-stable-latex-image":
            f"From {tag_date_iso} version of base dev image.",
        "docker-debian-stable-python-image":
            f"From {tag_date_iso} version of base dev image.",
        "docker-debian-testing-dev-image-base":
            f"From {tag_date_iso} version of Debian testing.",
        "docker-debian-testing-cpp-image-base":
            f"From {tag_date_iso} version of base dev image.",
        "docker-debian-testing-cpp-image-clang":
            f"From {tag_date_iso} version of base cpp image.",
        "docker-debian-testing-cpp-image-gcc":
            f"From {tag_date_iso} version of base cpp image.",
        "docker-debian-testing-python-image":
            f"From {tag_date_iso} version of base dev image.",
    }
    if not folder.absolute():
        folder = pathlib.Path(__file__).resolve().parent / folder
    for repo in repos:
        print(f"In repo {repo}")
        repo_path = folder / pathlib.Path(repo)
        print(f"    Updating Dockerfile")
        # Update Dockerfile in repo, replacing old tag references with new tag
        with open(repo_path / "Dockerfile") as file:
            content = file.read()
        match = re.search("[0-9]{8}", content)
        offset = 0
        while match:
            content = (content[0:match.start() + offset]
                       + tag_date
                       + content[match.end() + offset:])
            offset += match.end()
            match = re.search("[0-9]{8}", content[offset:])
        match = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}", content)
        offset = 0
        while match:
            content = (content[0:match.start() + offset]
                       + tag_date_iso
                       + content[match.end() + offset:])
            offset += match.end()
            match = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}", content[offset:])
        with open(repo_path / "Dockerfile", 'w', newline='\n') as file:
            file.write(content)

        # Commit changes to Dockerfile (if any)
        print("    Committing changes")
        git_repo = Repo(repo_path)
        diff = git_repo.git.diff(git_repo.head.commit.tree)
        if diff:
            index = git_repo.index
            index.add([str((repo_path / "Dockerfile").resolve())])
            author = Actor("Fredrik Andersson", "fredrik.andersson@industrialpathsolutions.com")
            index.commit(commit_messages[repo], author=author, committer=author)

        # Remove any existing tag
        tag = get_tag(git_repo, tag_date_iso)
        if tag:
            print("    Removing existing tag")
            git_repo.delete_tag(tag)
            git_repo.remotes.origin.push(refspec=f":refs/tags/{tag_date_iso}")

        # Tag latest commit
        print("    Tagging commit")
        new_tag = git_repo.create_tag(tag_date_iso, message=tag_messages[repo])

        if push:
            # Push changes to origin
            print("    Pushing changes to GitHub")
            git_repo.remotes.origin.push(force=True)
            git_repo.remotes.origin.push(new_tag)


if __name__ == "__main__":
    update_fa_repos("20230612")
