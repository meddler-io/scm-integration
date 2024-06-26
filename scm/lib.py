import aiohttp
import asyncio
import json


async def put_data(url, headers={}, data={}):
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=data) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            return await response.json()

async def post_data(url, headers={}, data={}):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            return await response.json()


async def get_data(url, headers={}, data={}):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, json=data) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            return await response.json()



async def get_scm_data(platform, access_token, update_callback):
    try:
        all_data = {
            'organizations': [],
            'projects': [],
            'repositories': []
        }

        async with aiohttp.ClientSession() as session:
            session.callback = update_callback
            if platform == 'bitbucket':
                
                session.schema = 'organizations'
                organizations = await get_bitbucket_workspaces(session, access_token)
                all_data['organizations'] = organizations
                
                for organization in organizations:
                    session.schema = 'projects'
                    projects = await get_bitbucket_projects(session, access_token, organization['slug'])
                    all_data['projects'].extend(projects)
                    
                    session.schema = 'repositories'
                    repositories = await get_bitbucket_repositories(session, access_token, organization['slug'])
                    all_data['repositories'].extend(repositories)

            elif platform == 'github':
                
                session.schema = 'organizations'
                organizations = await get_github_organizations(session, access_token)
                all_data['organizations'] = organizations
                
                session.schema = 'repositories'
                repositories = await get_github_repositories(session, access_token)
                all_data['repositories'] = repositories

            elif platform == 'gitlab':
                
                
                # personal_projects
                session.schema = 'repositories'
                personal_projects_repos = await get_gitlab_personal_projects(session, access_token  )
                all_data['repositories'].extend(personal_projects_repos)  # Treat subgroups as organizations
                
                
                # 
                session.schema = 'organizations'
                organizations = await get_gitlab_groups(session, access_token)
                all_data['organizations'] = organizations
                
                # 
                
                for organization in organizations:
                    session.schema = 'organizations'
                    subgroups = await get_gitlab_subgroups(session, access_token, organization['id'])
                    all_data['organizations'].extend(subgroups)  # Treat subgroups as organizations
                    
                    
                    session.schema = 'projects'
                    projects = await get_gitlab_projects(session, access_token, organization['id'])
                    all_data['projects'].extend(projects)
                    
                    for project in projects:
                        
                        session.schema = 'repositories'
                        repositories = await get_gitlab_repositories(session, access_token, project['id'])
                        all_data['repositories'].extend(repositories)

        return all_data

    except Exception as e:
        print(f"An error occurred while fetching data: {e}")
        return None

async def get_paginated_results(session, url, headers):
    results = []
    callback = session.callback
    schema = session.schema
    print("get_paginated_results", get_paginated_results)
    while url:
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if isinstance(data, dict):
                    results = data.get('values', []) if 'values' in data else []
                    await callback( { schema:  results } )
                    
                    url = data.get('next')  # Bitbucket uses 'next' for pagination
                elif isinstance(data, list):
                    results = data
                    await callback( { schema:  results } )
                    
                    url = None
                else:
                    url = None
            elif response.status == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limit hit. Retrying after {retry_after} seconds.")
                await asyncio.sleep(retry_after)
            else:
                print(f"Failed to fetch data: {response.status}")
                break
    return results

async def get_bitbucket_workspaces(session, access_token):
    url = 'https://api.bitbucket.org/2.0/workspaces'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_bitbucket_projects(session, access_token, workspace_slug):
    url = f'https://api.bitbucket.org/2.0/workspaces/{workspace_slug}/projects'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_bitbucket_repositories(session, access_token, workspace_slug):
    url = f'https://api.bitbucket.org/2.0/repositories/{workspace_slug}'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_github_organizations(session, access_token):
    url = 'https://api.github.com/user/orgs'
    headers = {'Authorization': f'{access_token}', 'Accept': 'application/vnd.github.v3+json'}
    return await get_paginated_results(session, url, headers)

async def get_github_repositories(session, access_token):
    url = 'https://api.github.com/user/repos'
    headers = {'Authorization': f'{access_token}', 'Accept': 'application/vnd.github.v3+json'}
    return await get_paginated_results(session, url, headers)

async def get_gitlab_groups(session, access_token):
    url = 'https://gitlab.com/api/v4/groups'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_gitlab_subgroups(session, access_token, group_id):
    url = f'https://gitlab.com/api/v4/groups/{group_id}/subgroups'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_gitlab_projects(session, access_token, group_id):
    url = f'https://gitlab.com/api/v4/groups/{group_id}/projects'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)

async def get_gitlab_personal_projects(session, access_token):
    url = f'https://gitlab.com/api/v4/projects?owned=true'
    headers = {'Authorization': f'{access_token}'}
    return await get_paginated_results(session, url, headers)



async def get_gitlab_repositories(session, access_token, project_id):
    # GitLab does not have a separate concept of repositories; projects are repositories
    return []

# Example usage
platform = 'bitbucket'  # Change platform as needed ('bitbucket', 'github', or 'gitlab')
access_token = 'oAuth_token'

if __name__ == "__main__":
    data = asyncio.run(get_scm_data(platform, access_token))
    if data:
        print("All data fetched successfully:")
        with open(f"{platform}.json", "w") as outfile:
            json.dump(data, outfile)
    else:
        print("Failed to fetch data.")
