from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'mock-idp'})

@app.route('/sso', methods=['GET'])
def sso():
    # Mock SSO endpoint
    return jsonify({'message': 'Mock IDP SSO endpoint'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)

