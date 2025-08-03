from flask import Flask, render_template, request, jsonify
from app.ma

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    url = request.json.get('url')
    # Simulate generated text (replace with actual logic)
    generated_1 = f"Generated content for: {url}\n\n" + "Lorem ipsum " * 400
    generated_2 = f"Summary or alternate output:\n\n" + "Dolor sit amet " * 80
    return jsonify({'output1': generated_1, 'output2': generated_2})

if __name__ == '__main__':
    app.run(debug=True)
