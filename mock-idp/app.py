from flask import Flask, request, jsonify, redirect, session, url_for
from flask_cors import CORS
import jwt
import secrets
import base64
from urllib.parse import urlencode, parse_qs
import time

from constants import JWT_SECRET, IDP_SECRET_KEY, OAUTH_AUDIENCE, OAUTH_ISSUER, FRONTEND_URL

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = IDP_SECRET_KEY

# Mock AD group to role mapping
AD_GROUP_ROLE_MAPPING = {
    'PackageManager-Admins': 'admin',
    'PackageManager-Approvers': 'approver', 
    'PackageManager-Users': 'user',
    # Add more AD groups as needed
}

# Mock user database
MOCK_USERS = {
    'admin': {
        'username': 'admin',
        'email': 'admin@company.com',
        'full_name': 'System Administrator',
        'password': 'admin',  # In real implementation, this would be hashed
        'ad_groups': ['PackageManager-Admins', 'Domain Admins']
    },
    'approver': {
        'username': 'approver',
        'email': 'approver@company.com', 
        'full_name': 'Package Approver',
        'password': 'approver',
        'ad_groups': ['PackageManager-Approvers', 'Domain Users']
    },
    'user': {
        'username': 'user',
        'email': 'user@company.com',
        'full_name': 'Regular User', 
        'password': 'user',
        'ad_groups': ['PackageManager-Users', 'Domain Users']
    }
}

# Store authorization codes temporarily (in production, use Redis or database)
authorization_codes = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'mock-idp'})

# OAuth2/OpenID Connect Discovery
@app.route('/.well-known/openid_configuration', methods=['GET'])
def openid_configuration():
    """OpenID Connect Discovery endpoint"""
    base_url = request.url_root.rstrip('/')
    return jsonify({
        'issuer': base_url,
        'authorization_endpoint': f'{base_url}/oauth/authorize',
        'token_endpoint': f'{base_url}/oauth/token',
        'userinfo_endpoint': f'{base_url}/oauth/userinfo',
        'jwks_uri': f'{base_url}/oauth/jwks',
        'response_types_supported': ['code', 'id_token', 'token'],
        'grant_types_supported': ['authorization_code', 'implicit'],
        'subject_types_supported': ['public'],
        'id_token_signing_alg_values_supported': ['HS256', 'RS256']
    })

# OAuth2 Authorization Endpoint
@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    """OAuth2 Authorization endpoint - handles both GET (redirect) and POST (form submission)"""
    if request.method == 'GET':
        # Display login form
        client_id = request.args.get('client_id')
        redirect_uri = request.args.get('redirect_uri')
        response_type = request.args.get('response_type')
        state = request.args.get('state')
        scope = request.args.get('scope', 'openid profile email')
        
        # Store parameters in session for after login
        session['oauth_params'] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': response_type,
            'state': state,
            'scope': scope
        }
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Mock IDP Login</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input[type="text"], input[type="password"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
                button { background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                .user-list { margin-top: 20px; }
                .user-item { padding: 10px; border: 1px solid #ddd; margin: 5px 0; cursor: pointer; background: #f9f9f9; }
                .user-item:hover { background: #e9e9e9; }
            </style>
        </head>
        <body>
            <h2>Mock IDP Login</h2>
            <form method="POST">
                <div class="form-group">
                    <label>Username:</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit">Login</button>
            </form>
            
            <div class="user-list">
                <h3>Quick Login (click to use):</h3>
                <div class="user-item" onclick="quickLogin('admin', 'admin')">Admin (admin/admin)</div>
                <div class="user-item" onclick="quickLogin('approver', 'approver')">Approver (approver/approver)</div>
                <div class="user-item" onclick="quickLogin('user', 'user')">User (user/user)</div>
            </div>
            
            <script>
                function quickLogin(username, password) {
                    document.querySelector('input[name="username"]').value = username;
                    document.querySelector('input[name="password"]').value = password;
                    document.querySelector('form').submit();
                }
            </script>
        </body>
        </html>
        '''
    
    else:  # POST - process login
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in MOCK_USERS and MOCK_USERS[username]['password'] == password:
            user = MOCK_USERS[username]
            
            # Generate authorization code
            auth_code = secrets.token_urlsafe(32)
            authorization_codes[auth_code] = {
                'user': user,
                'expires_at': time.time() + 600,  # 10 minutes
                'params': session.get('oauth_params', {})
            }
            
            # Redirect back to client with authorization code
            oauth_params = session.get('oauth_params', {})
            redirect_uri = oauth_params.get('redirect_uri', FRONTEND_URL)
            state = oauth_params.get('state', '')
            
            params = {
                'code': auth_code,
                'state': state
            }
            
            return redirect(f"{redirect_uri}?{urlencode(params)}")
        else:
            return "Invalid credentials", 401

# OAuth2 Token Endpoint
@app.route('/oauth/token', methods=['POST'])
def token():
    """OAuth2 Token endpoint"""
    grant_type = request.form.get('grant_type')
    code = request.form.get('code')
    redirect_uri = request.form.get('redirect_uri')
    client_id = request.form.get('client_id')
    
    if grant_type != 'authorization_code':
        return jsonify({'error': 'unsupported_grant_type'}), 400
    
    if code not in authorization_codes:
        return jsonify({'error': 'invalid_grant'}), 400
    
    auth_data = authorization_codes[code]
    if time.time() > auth_data['expires_at']:
        del authorization_codes[code]
        return jsonify({'error': 'invalid_grant'}), 400
    
    user = auth_data['user']
    
    # Map AD groups to roles
    user_role = 'user'  # Default role
    for group in user['ad_groups']:
        if group in AD_GROUP_ROLE_MAPPING:
            user_role = AD_GROUP_ROLE_MAPPING[group]
            break
    
    # Generate JWT tokens
    now = int(time.time())
    access_token_payload = {
        'sub': user['username'],
        'iss': request.url_root.rstrip('/'),
        'aud': client_id,
        'iat': now,
        'exp': now + 3600,  # 1 hour
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'role': user_role,
        'ad_groups': user['ad_groups']
    }
    
    id_token_payload = {
        'sub': user['username'],
        'iss': request.url_root.rstrip('/'),
        'aud': client_id,
        'iat': now,
        'exp': now + 3600,
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'role': user_role,
        'ad_groups': user['ad_groups']
    }
    
    secret_key = JWT_SECRET
    access_token = jwt.encode(access_token_payload, secret_key, algorithm='HS256')
    id_token = jwt.encode(id_token_payload, secret_key, algorithm='HS256')
    
    print(f"Generated access token: {access_token[:50]}...")
    print(f"Access token payload: {access_token_payload}")
    
    # Clean up authorization code
    del authorization_codes[code]
    
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'id_token': id_token
    })

# OAuth2 UserInfo Endpoint
@app.route('/oauth/userinfo', methods=['GET'])
def userinfo():
    """OAuth2 UserInfo endpoint"""
    import sys
    print("=== USERINFO ENDPOINT CALLED ===", flush=True)
    print(f"Request method: {request.method}", flush=True)
    print(f"Request headers: {dict(request.headers)}", flush=True)
    
    auth_header = request.headers.get('Authorization')
    print(f"Authorization header: {auth_header}", flush=True)
    
    if not auth_header or not auth_header.startswith('Bearer '):
        print("No valid Authorization header", flush=True)
        return jsonify({'error': 'invalid_token'}), 401
    
    token = auth_header.split(' ')[1]
    print(f"Token received: {token[:50]}...", flush=True)
    
    try:
        # Decode token with audience validation
        payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=['HS256'],
            audience=OAUTH_AUDIENCE,  # Validate audience
            issuer=OAUTH_ISSUER      # Validate issuer
        )
        print(f"Token decoded successfully: {payload}", flush=True)
        return jsonify({
            'sub': payload['sub'],
            'username': payload['username'],
            'email': payload['email'],
            'full_name': payload['full_name'],
            'role': payload['role']
        })
    except jwt.InvalidTokenError as e:
        print(f"Token validation failed: {e}", flush=True)
        return jsonify({'error': 'invalid_token'}), 401
    except Exception as e:
        print(f"Unexpected error: {e}", flush=True)
        return jsonify({'error': 'internal_error'}), 500

# JWKS Endpoint (for token verification)
@app.route('/oauth/jwks', methods=['GET'])
def jwks():
    """JSON Web Key Set endpoint"""
    return jsonify({
        'keys': [
            {
                'kty': 'oct',
                'kid': 'mock-key-1',
                'k': base64.urlsafe_b64encode(JWT_SECRET.encode()).decode().rstrip('=')
            }
        ]
    })

@app.route('/sso', methods=['GET'])
def sso():
    # Mock SSO endpoint
    return jsonify({'message': 'Mock IDP SSO endpoint'})

@app.route('/auth/validate', methods=['POST'])
def validate_token():
    """Validate token and return user info with role mapping"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token required'}), 400
        
        # In a real implementation, you would validate the token with your AD provider
        # For now, we'll mock the validation
        mock_user_data = {
            'username': 'john.doe',
            'email': 'john.doe@company.com',
            'full_name': 'John Doe',
            'ad_groups': ['PackageManager-Users', 'Domain Users']  # Mock AD groups
        }
        
        # Map AD groups to roles
        user_role = 'user'  # Default role
        for group in mock_user_data['ad_groups']:
            if group in AD_GROUP_ROLE_MAPPING:
                user_role = AD_GROUP_ROLE_MAPPING[group]
                break  # Use the first matching role (highest privilege)
        
        return jsonify({
            'valid': True,
            'user': {
                'username': mock_user_data['username'],
                'email': mock_user_data['email'],
                'full_name': mock_user_data['full_name'],
                'role': user_role,
                'ad_groups': mock_user_data['ad_groups']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/groups', methods=['GET'])
def get_available_groups():
    """Get available AD groups for role mapping"""
    return jsonify({
        'groups': list(AD_GROUP_ROLE_MAPPING.keys()),
        'mapping': AD_GROUP_ROLE_MAPPING
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)

