from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import json
import os
from datetime import datetime

RESPONSES_FILE = "responses/responses.json"

def get_participant_id():
    if 'participant_id' not in session:
        session['participant_id'] = f"participant_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return session['participant_id']

def update_participant_data(section, data):
    os.makedirs('responses', exist_ok=True)
    pid = get_participant_id()

    # Load or initialize the file
    if os.path.exists(RESPONSES_FILE):
        with open(RESPONSES_FILE, 'r') as f:
            all_data = json.load(f)
    else:
        all_data = {}

    # Load participant block
    if pid not in all_data:
        all_data[pid] = {'participant_id': pid}

    if section == 'round':
        all_data[pid].setdefault('rounds', []).append(data)
    else:
        all_data[pid][section] = data

    # Save updated structure
    with open(RESPONSES_FILE, 'w') as f:
        json.dump(all_data, f, indent=4)

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
        gender_self = request.form.get('gender_self_describe')
        age_group = request.form.get('age_group')
        country = request.form.get('country')
        other_country = request.form.get('other_country')
        occupation = request.form.get('occupation')
        other_occupation = request.form.get('other_occupation')

        if gender == 'Self-describe':
            gender = gender_self.strip() if gender_self else 'Self-describe'
        if country == 'Other':
            country = other_country.strip() if other_country else 'Other'
        if occupation == 'Other':
            occupation = other_occupation.strip() if other_occupation else 'Other'

        if age_group == '15 or younger':
            return render_template('thank_you.html', message="Sorry, you do not meet the age criteria for this study.")

        update_participant_data('demographics', {
            'gender': gender,
            'age_group': age_group,
            'country': country,
            'occupation': occupation
        })

        session['round'] = 1
        return redirect(url_for('pre_questionnaire'))

    return render_template('demographics.html')

@app.route('/pre-questionnaire', methods=['GET', 'POST'])
def pre_questionnaire():
    if request.method == 'POST':
        data = {
            'news_frequency': request.form.get('news_frequency'),
            'device': request.form.get('device'),
            'device_other': request.form.get('device_other') if request.form.get('device') == 'Other' else None,
            'platform': request.form.get('platform'),
            'platform_other': request.form.get('platform_other') if request.form.get('platform') == 'Other' else None,
            'news_sources': request.form.get('news_sources'),
            'attention_check': request.form.get('attention_check'),
            'trust_level': request.form.get('trust_level')
        }

        update_participant_data('pre_questionnaire', data)

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
        # Get selected elements (checkboxes)
        selection_elements = request.form.getlist('choice_elements')
        other_text = request.form.get('other_element')

        # Validation: at least one must be selected
        if not selection_elements:
            return render_template('mid_questionnaire.html', error="Please select at least one element that influenced your choice.")

        # Validation logic
        other_selected = 'Other (please specify)' in selection_elements
        none_selected = "Don't know / None of these" in selection_elements

        if other_selected and not other_text:
            return render_template('mid_questionnaire.html', error="Please specify what 'Other' means.")
        if none_selected and len(selection_elements) > 1:
            return render_template('mid_questionnaire.html', error="'Don't know' cannot be selected with other options.")
        if other_selected and len(selection_elements) == 1:
            selection_elements = [f"Other: {other_text}"]

        # Likert scale responses
        trust_article = request.form.get('trust_article')
        trust_image = request.form.get('trust_image')

        # Save data with article reference
        update_participant_data('round', {
            'round': session.get('round', 1),
            'article_id': session.get('next_article'),
            'mid_questionnaire': {
                'selected_elements': selection_elements,
                'trust_article': trust_article,
                'trust_image': trust_image
            }
        })

        # Determine next step
        if session.get('round', 1) < 3:
            session['round'] += 1
            next_article_id = session.get('next_article')
            if next_article_id is not None:
                return redirect(url_for('article', article_id=next_article_id))
            else:
                return redirect(url_for('select_article'))
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
