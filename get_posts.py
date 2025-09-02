import json
import time
import os
import requests
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import timedelta

tzinfos = {"EST": -21600}

start_id = int(requests.get(f"{os.environ.get('STATUS_URL')}?action=start").text)

completed = []

current_post_count = 0
response = requests.get("https://scratch.mit.edu/discuss/", headers={"Cookie": f'scratchsessionsid={os.environ.get('SCRATCH_TOKEN')}'})
root = BeautifulSoup(response.text, "html.parser")
output = root.select("td.tcr > a")
latest_posts = []
for latest_post in output:
    latest_posts.append(int(latest_post.get("href").split("/")[3]))

latest_posts.sort(reverse=True)
max_id = latest_posts[0]

print("Starting at", start_id, "with max", max_id, "and", max_id - start_id, "new posts to get")

skipped = 0
post_string = []
for id in range(start_id, max_id + 1):
    if id in completed:
        skipped += 1
        continue
    if skipped > 0:
        print("Skipped", skipped, "posts")
        skipped = 0
    response = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
    if response.status_code == 503:
        time.sleep(10)
        response = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
        if response.status_code == 503:
            time.sleep(10)
            response = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
            if response.status_code == 503:
                time.sleep(10)
                response = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
                if response.status_code == 503:
                    time.sleep(10)
                    response = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
    print("Post", id, "is", response.status_code)
    if response.status_code == 404 or response.status_code == 403:
        post_string.append(f'{id},{response.status_code},,\n')
        completed.append(id)
        continue
    
    root = BeautifulSoup(response.text, "html.parser")

    posts = root.find_all("div", attrs={"class": "blockpost"})
    target_post = root.select_one(f"#p{id}")
    attempts = 0
    while not target_post and attempts < 10:
        print("trying again, attempt", attempts)
        response2 = requests.get(f"https://scratch.mit.edu/discuss/post/{id}")
        root2 = BeautifulSoup(response2.text, "html.parser")
        posts = root2.find_all("div", attrs={"class": "blockpost"})
        target_post = root2.select_one("#p" + str(id))
        attempts += 1

    category = int(root.select_one(".linkst ul li:nth-child(2) a").get("href").split("/")[2])
    gained = 0
    for post in posts:
        username = post.find("a", attrs={"class": "black username"}).text
        el = post.find("span", attrs={"class": "conr"}).next_sibling

        post_id = int(el.get("href").split("/")[3])
        if "Today" in el.text or "Yesterday" in el.text:
            offset = 0
            if "Yesterday" in el.text:
                offset = 1
            else:
                pass
            date = int((parser.parse(el.text.split(" ")[1] + " EST", tzinfos=tzinfos) - timedelta(offset)).timestamp())
        else:
            date = int(parser.parse(el.text + " EST", tzinfos=tzinfos).timestamp())
        if (not post_id in completed) and (post_id >= start_id):
            if post_id <= max_id:
                gained += 1
                print(post_id, "by", username, "on", date, "in category", category)
                completed.append(post_id)
                post_string.append(f'{post_id},{category},{username},{date}\n')
            else:
                print("Passing up", post_id)
    if gained > 0:
        print("Added", gained, "new posts")

post_string.sort(key=lambda item: int(item.split(",")[0]))
print("Done with", len(post_string), "new posts")

print("Saving progress", max_id + 1)
requests.get(f"{os.environ.get('STATUS_URL')}?action=start&value=" + str(max_id + 1))

output = ""
for p in post_string:
    output += p

print("Saving new data")
requests.post(os.environ.get('NEW_DATA_URL'), data=output)

for p in post_string: print(p, end="")
