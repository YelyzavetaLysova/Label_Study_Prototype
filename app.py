from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    selected_category = None
    if request.method == 'POST':
        selected_category = request.form.get('category')
    return render_template('index.html', selected_category=selected_category)

if __name__ == '__main__':
    app.run(debug=True)
