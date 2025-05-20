from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import json
import os
from datetime import datetime

# Utility to generate or reuse participant file
def get_participant_file():
    os.makedirs('responses', exist_ok=True)
    participant_id = session.get('participant_id')
    if not participant_id:
        participant_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session['participant_id'] = participant_id
    return f"responses/{participant_id}.json"

# Utility to update the participant file with structured data
def update_participant_data(key, data):
    filename = get_participant_file()
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = json.load(f)
    else:
        content = {"participant_id": session['participant_id']}
    
    if key == 'round':
        content.setdefault('rounds', []).append(data)
    else:
        content[key] = data
    
    with open(filename, 'w') as f:
        json.dump(content, f, indent=4)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load articles
df = pd.read_csv('articles.csv')
df.reset_index(inplace=True)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/demographics', methods=['GET', 'POST'])
def demographics():
    if request.method == 'POST':
        gender = request.form.get('gender')
        self_described_gender = request.form.get('self_described_gender') or None
        age_group = request.form.get('age')
        country = request.form.get('country')

        if age_group == '15 or younger – END SURVEY':
            return render_template('thank_you.html', message="Sorry, you do not meet the age criteria for this study.")

        # Save structured demographic data
        update_participant_data('demographics', {
            'gender': gender,
            'self_described_gender': self_described_gender,
            'age_group': age_group,
            'country': country
        })

        session['round'] = 1
        return redirect(url_for('pre_questionnaire'))

    return render_template('demographics.html')



@app.route('/pre-questionnaire', methods=['GET', 'POST'])
def pre_questionnaire():
    if request.method == 'POST':
        update_participant_data('pre_questionnaire', {
            'news_frequency': request.form.get('news_frequency')
        })
        return redirect(url_for('select_article'))
    return render_template('pre_questionnaire.html')

@app.route('/select-article')
def select_article():
    round_number = session.get('round', 1)
    grouped = df.groupby(df['Category'].str.title()).first()
    grouped.index.name = None
    first_articles = grouped.reset_index().head(4)
    return render_template('select_article.html', articles=first_articles.to_dict(orient='records'))

@app.route('/article/<int:article_id>', methods=['GET', 'POST'])
def article(article_id):
    if article_id >= len(df):
        return redirect(url_for('select_article'))
    if request.method == 'POST':
        selected_article_id = int(request.form['selected_article_id'])
        session['next_article'] = selected_article_id
        update_participant_data('round', {
            'round': session.get('round', 1),
            'selected_article_id': selected_article_id,
            'selected_article_title': df.iloc[selected_article_id]['Title']
        })
        return redirect(url_for('mid_questionnaire'))
    article_data = df.iloc[article_id].to_dict()
    recommendations = df[(df['Category'] == article_data['Category']) & (df['index'] != article_id)].head(4).to_dict(orient='records')
    return render_template('article.html', article=article_data, recommendations=recommendations)

@app.route('/mid-questionnaire', methods=['GET', 'POST'])
def mid_questionnaire():
    if request.method == 'POST':
        update_participant_data('round', {
            'round': session.get('round', 1),
            'mid_questionnaire': {
                'usefulness': request.form.get('usefulness')
            }
        })
        if session.get('round', 1) < 3:
            session['round'] += 1
            next_article_id = session.get('next_article')
            if next_article_id is None:
                return redirect(url_for('post_questionnaire'))
            return redirect(url_for('article', article_id=next_article_id))
        else:
            return redirect(url_for('post_questionnaire'))
    return render_template('mid_questionnaire.html')

@app.route('/post-questionnaire', methods=['GET', 'POST'])
def post_questionnaire():
    if request.method == 'POST':
        update_participant_data('post_questionnaire', {
            'confidence': request.form.get('confidence'),
            'feedback': request.form.get('feedback')
        })
        return redirect(url_for('thank_you'))
    return render_template('post_questionnaire.html')

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    app.run(debug=True)
