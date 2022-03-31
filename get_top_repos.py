import requests

PASSWORD = os.environ["PASSWORD"]
headers = {"Authorization": "bearer %s" % PASSWORD}


def run_query(query):
    request = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

repo_urls = []
cursor = "null"

for i in range(10):
    query = """
    {
    search(query: "stars:>1000", type: REPOSITORY, first: 100, after: %s) {
        pageInfo {
        endCursor
        startCursor
        }
        edges {
        node {
            ... on Repository {
            url
            }
        }
        }
    }
    }
    """ % cursor

    result = run_query(query)
    for edge in result["data"]["search"]["edges"]:
        repo_urls.append(edge["node"]["url"])

    cursor = '"%s"' % result["data"]["search"]["pageInfo"]["endCursor"]

with open("repo_urls", "w") as f:
    for repo_url in repo_urls:
        f.write(repo_url + "\n")

print(repo_urls)
