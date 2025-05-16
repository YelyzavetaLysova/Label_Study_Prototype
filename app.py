from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure random key

# Load articles from CSV
df = pd.read_csv('articles.csv')
df.reset_index(inplace=True)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/demographics', methods=['GET', 'POST'])
def demographics():
    if request.method == 'POST':
        session['round'] = 1
        return redirect(url_for('pre_questionnaire'))
    return render_template('demographics.html')

@app.route('/pre-questionnaire', methods=['GET', 'POST'])
def pre_questionnaire():
    if request.method == 'POST':
        return redirect(url_for('select_article'))
    return render_template('pre_questionnaire.html')

@app.route('/select-article')
def select_article():
    round_number = session.get('round', 1)

    # Group globally by category to always get 4 unique categories
    grouped = df.groupby(df['Category'].str.title()).first()
    grouped.index.name = None
    first_articles = grouped.reset_index().head(4)

    # Debug: print how many articles are selected and their categories
    print(f"Round {round_number}: Providing {len(first_articles)} articles from categories: {list(first_articles['Category'])}")

    return render_template('select_article.html', articles=first_articles.to_dict(orient='records'))




@app.route('/article/<int:article_id>', methods=['GET', 'POST'])
def article(article_id):
    if article_id >= len(df):
        return redirect(url_for('select_article'))
    
    if request.method == 'POST':
        session['next_article'] = int(request.form['selected_article_id'])
        return redirect(url_for('mid_questionnaire'))

    article = df.iloc[article_id].to_dict()
    recommendations = df[(df['Category'] == article['Category']) & (df['index'] != article_id)].head(4).to_dict(orient='records')
    return render_template('article.html', article=article, recommendations=recommendations)

@app.route('/mid-questionnaire', methods=['GET', 'POST'])
def mid_questionnaire():
    if request.method == 'POST':
        if session.get('round', 1) < 3:
            session['round'] += 1
            next_article_id = session.get('next_article')
            if next_article_id is None:
                # Safety check if next_article is missing
                return redirect(url_for('post_questionnaire'))
            return redirect(url_for('article', article_id=next_article_id))
        else:
            return redirect(url_for('post_questionnaire'))
    return render_template('mid_questionnaire.html')


@app.route('/post-questionnaire', methods=['GET', 'POST'])
def post_questionnaire():
    if request.method == 'POST':
        return redirect(url_for('thank_you'))
    return render_template('post_questionnaire.html')

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    app.run(debug=True)
