import os
import subprocess
import tempfile
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/diagnostics')
def diagnostics():
    import requests
    api_url = os.environ.get('ACTUAL_HTTP_API_URL')
    api_key = os.environ.get('ACTUAL_HTTP_API_KEY')
    sync_id = os.environ.get('ACTUAL_SYNCID')
    
    if not api_url or not api_key or not sync_id:
        return jsonify({
            'status': 'ERROR',
            'error': 'Missing connection environment variables',
            'env_keys_present': {
                'ACTUAL_HTTP_API_URL': bool(api_url),
                'ACTUAL_HTTP_API_KEY': bool(api_key),
                'ACTUAL_SYNCID': bool(sync_id)
            }
        }), 400
        
    try:
        url = api_url.rstrip('/') + f'/v1/budgets/{sync_id}/accounts'
        r = requests.get(url, headers={'x-api-key': api_key}, timeout=5)
        if r.status_code == 200:
            accounts = r.json().get('data', [])
            return jsonify({
                'status': 'OK',
                'api_connection': 'SUCCESS',
                'api_url': api_url,
                'sync_id': sync_id,
                'accounts_count': len(accounts),
                'accounts': [{'id': a.get('id'), 'name': a.get('name'), 'offbudget': a.get('offbudget')} for a in accounts]
            })
        else:
            return jsonify({
                'status': 'ERROR',
                'api_connection': 'FAILED',
                'status_code': r.status_code,
                'response': r.text[:200]
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'api_connection': 'EXCEPTION',
            'error': str(e)
        }), 500


@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    execute = request.form.get('execute') == 'true'
    force = request.form.get('force') == 'true'
    days = request.form.get('days', '3')

    # Validate days is an integer
    try:
        days_int = int(days)
    except ValueError:
        days_int = 3

    # Save to a temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, 'uploaded_orders.csv')
    file.save(temp_path)

    try:
        # Prepare subprocess environment, inheriting from current environment
        env = os.environ.copy()
        
        # Build command
        cmd = ['python3', 'actual-amazon-noter']
        if execute:
            cmd.append('--execute')
        else:
            cmd.extend(['--dry-run', 'csv'])
            
        if force:
            cmd.append('--force')
            
        cmd.extend(['--days', str(days_int)])
        cmd.append(temp_path)

        # Run subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        stdout = result.stdout
        stderr = result.stderr
        success = result.returncode == 0

        # Clean output a bit (e.g. remove full temporary path references)
        stdout = stdout.replace(temp_path, 'uploaded_orders.csv')
        stderr = stderr.replace(temp_path, 'uploaded_orders.csv')

        return jsonify({
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': result.returncode
        })

    except Exception as e:
        return jsonify({'error': f'Execution failed: {str(e)}'}), 500
    finally:
        # Ensure temporary file cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
