import json
import shutil
import os
from pathlib import Path
from git import Repo
from github import Github
import time
import logging
import re
from guess_language import guess_language

if not os.path.isdir("logs"):
    os.mkdir("logs")
logging.basicConfig(
    filename = "logs/%d.log" % int(time.time()),
    filemode = "w",
    format = "%(asctime)s: %(levelname)s - %(message)s",
    level = logging.INFO
)

# Load subs
subs = {}
with open("subs.json") as f:
    subs_raw = json.load(f)

    for sub in subs_raw:
        for term in sub["search"]:
            subs[term] = sub["suggest"][0]
            subs[term.upper()] = sub["suggest"][0].upper()
            subs[term.title()] = sub["suggest"][0].title()

logging.info("Got subs")

# Load repos
repo_urls = []
with open("repo_urls") as f:
    for repo_url in f:
        repo_urls.append(repo_url.rstrip())

logging.info("Got repos")

shutil.rmtree("./repos")

USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]
BRANCH_NAME = "switch-to-inclusive-terms"
TITLE = "Switch to gender neutral terms"
DESCRIPTION = "\
Hey! We noticed your repository had a few instances of gendered language. We've attempted to make the changes to gender neutral language using these substitions - [joelparkerhenderson/gender-inclusive-language](https://github.com/joelparkerhenderson/gender-inclusive-language). These are not always perfect, but we hope they will assist maintainers in finding and fixing issues :)\n\n\
You can learn more about this project and why gender neutral language matters at [inclusivecoding.wixsite.com](https://inclusivecoding.wixsite.com/home). If you have feedback for this bot, please provide it [here](https://forms.gle/MnEH24gWbzPLSnnv7).\
"
g = Github(PASSWORD)

# Go through all repos
for i in range(len(repo_urls)):
    try:
        repo_url = repo_urls[i]
        logging.info("Working on repo %s" % repo_url)

        repo_dir = "./repos/%d" % i
        repo = Repo.clone_from(repo_url, repo_dir)
        repo.config_writer().set_value("user", "name", USERNAME).release()
        repo.config_writer().set_value("user", "email", USERNAME + "@github.com").release()

        logging.info("Done cloning repo")
    
        head = repo.git.checkout("-b", BRANCH_NAME)

        changed = False
        for path in Path(repo_dir).rglob("*"):
            if ".git" in str(path) or os.path.isdir(path):
                continue
            
            is_md = str(path).endswith(".md") or str(path).endswith(".MD")

            try:
                with open(path, "r") as f:
                    data = f.read()

                if is_md:
                    language = guess_language(data)
                    if language != 'en':
                        # Probably not english
                        continue

                endings = [
                    b'\r\n',
                    b'\n\r',
                    b'\n',
                    b'\r',
                ]
                ending = None
                with open(path, 'rb') as fp:
                    for line in fp:
                        for x in endings:
                            if line.endswith(x):
                                ending = x.decode("utf-8")

                new_data = data
                for old, new in subs.items():
                    lines = new_data.split(ending)
                    for j, l in enumerate(lines):
                        trimmed_l = l.strip()
                        if ((trimmed_l.startswith("#") or trimmed_l.startswith("//")) or is_md) and 'http' not in l:
                            lines[j] = re.sub(rf"\b({old})\b", new, l, flags=re.MULTILINE)
                    new_data = ending.join(lines)

                if new_data != data:
                    changed = True
                    with open(path, "w") as f:
                        f.write(new_data)
            except Exception:
                continue

        if changed:
            logging.info("Made changes!")
            repo.git.add("*")
            repo.git.commit(m=TITLE)

            repoName = repo_url.removeprefix("https://github.com/")
            gRepo = g.get_repo(repoName)
            forkedRepo = gRepo.create_fork()

            remote = repo.create_remote("fork", "https://%s:%s@" % (USERNAME, PASSWORD) + forkedRepo.clone_url.removeprefix("https://"))
            repo.git.push("fork", BRANCH_NAME, "-f")

            gRepo.create_pull(
                title=TITLE,
                body=DESCRIPTION,
                base=gRepo.default_branch,
                head="%s:%s" % (USERNAME, BRANCH_NAME),
                draft=False
            )
        else:
            logging.info("No changes to be made")
    except Exception as e:
        logging.error(e)
    finally:
        if repo:
            logging.info("Deleting repo")
            shutil.rmtree(repo_dir)
    
logging.info("Done all repos")
