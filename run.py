from flask import Flask, render_template, request, jsonify
from app.crawler import create_llms
from app.alternatives import firecrawl_get

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    url = request.json.get('url')
    # Simulate generated text (replace with actual logic)
    generated_1 = create_llms(url)
    generated_2 = firecrawl_get(url)
    return jsonify({'output1': generated_1, 'output2': generated_2})

if __name__ == '__main__':
    app.run(debug=True)
