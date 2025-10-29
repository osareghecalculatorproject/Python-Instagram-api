from flask import Flask, jsonify, request
import requests
import json
from urllib.parse import quote

app = Flask(__name__)

# Common headers for Instagram requests
INSTAGRAM_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "x-ig-app-id": "936619743392459",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

# Note: The doc_id for GraphQL queries may change periodically (every few weeks). 
# Check recent sources or browser network requests to update it.
INSTAGRAM_POST_DOC_ID = "8845758582119845"  # As of 2025 sources

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    response = requests.get(url, headers=INSTAGRAM_HEADERS)
    
    if response.status_code == 200:
        data = response.json()['data']['user']
        profile = {
            'biography': data.get('biography'),
            'bio_links': data.get('bio_links', []),
            'followers': data['edge_followed_by']['count'],
            'following': data['edge_follow']['count'],
            'full_name': data.get('full_name'),
            'is_verified': data.get('is_verified'),
            'profile_pic_url': data.get('profile_pic_url_hd'),
            'posts_count': data['edge_owner_to_timeline_media']['count'],
            'recent_posts': []  # Up to 12 recent posts
        }
        
        for edge in data['edge_owner_to_timeline_media']['edges']:
            node = edge['node']
            post = {
                'id': node['id'],
                'shortcode': node['shortcode'],
                'display_url': node['display_url'],
                'likes': node['edge_liked_by']['count'],
                'comments': node['edge_media_to_comment']['count'],
                'is_video': node.get('is_video', False),
                'video_url': node.get('video_url') if node.get('is_video') else None,
                'caption': node['edge_media_to_caption']['edges'][0]['node']['text'] if node['edge_media_to_caption']['edges'] else None
            }
            profile['recent_posts'].append(post)
        
        return jsonify(profile)
    else:
        return jsonify({'error': f"Failed to fetch profile: {response.status_code}"}), response.status_code

@app.route('/post/<shortcode>', methods=['GET'])
def get_post(shortcode):
    variables = quote(json.dumps({
        'shortcode': shortcode,
        'fetch_tagged_user_count': None,
        'hoisted_comment_id': None,
        'hoisted_reply_id': None
    }, separators=(',', ':')))
    
    body = f"variables={variables}&doc_id={INSTAGRAM_POST_DOC_ID}"
    
    response = requests.post(
        "https://www.instagram.com/graphql/query",
        headers={**INSTAGRAM_HEADERS, "content-type": "application/x-www-form-urlencoded"},
        data=body
    )
    
    if response.status_code == 200:
        data = response.json()['data']['xdt_shortcode_media']
        post = {
            'id': data['id'],
            'shortcode': data['shortcode'],
            'display_url': data['display_url'],
            'likes': data['edge_media_preview_like']['count'],
            'comments': data['edge_media_to_parent_comment']['count'],
            'is_video': data.get('is_video', False),
            'video_url': data.get('video_url') if data.get('is_video') else None,
            'caption': data['edge_media_to_caption']['edges'][0]['node']['text'] if data['edge_media_to_caption']['edges'] else None,
            'owner': {
                'username': data['owner']['username'],
                'full_name': data['owner'].get('full_name')
            }
        }
        return jsonify(post)
    else:
        return jsonify({'error': f"Failed to fetch post: {response.status_code}"}), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
