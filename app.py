from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import secrets
import functools
import re
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    position = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidates = db.relationship('Candidate', backref='election', lazy=True)
    voter_keys = db.relationship('VoterKey', backref='election', lazy=True)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    votes = db.Column(db.Integer, default=0)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    voter_key_id = db.Column(db.Integer, db.ForeignKey('voter_key.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VoterKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20), unique=True, nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# Decorators
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please log in as admin first.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def voter_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('voter_key_id'):
            flash('Please enter a valid voter key.')
            return redirect(url_for('voter_login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_voter_key(election_position):
    year = datetime.now().year
    position_code = re.sub(r'[^A-Z]', '', election_position.upper())[:4].ljust(4, 'X')
    while True:
        # Generate a random 5-digit number
        random_num = str(random.randint(0, 99999)).zfill(5)
        key = f"{year}-{position_code}-{random_num}"
        # Check if this key already exists
        if not VoterKey.query.filter_by(key=key).first():
            return key

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'password':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/create-election', methods=['POST'])
@admin_required
def create_election():
    data = request.json
    num_voters = int(data.get('numVoters', 0))
    
    if num_voters < 2:
        return jsonify({'error': 'Number of voters must be at least 2'}), 400
    
    # Check if election title already exists
    existing_election = Election.query.filter_by(title=data['title']).first()
    if existing_election:
        return jsonify({'error': 'An election with this title already exists'}), 400
    
    election = Election(
        title=data['title'],
        position=data['position']
    )
    db.session.add(election)
    db.session.flush()
    
    # Create candidates
    for candidate_name in data['candidates']:
        candidate = Candidate(name=candidate_name, election_id=election.id)
        db.session.add(candidate)
    
    # Generate voter keys
    voter_keys = []
    for _ in range(num_voters):
        key = generate_voter_key(data['position'])
        voter_key = VoterKey(key=key, election_id=election.id)
        db.session.add(voter_key)
        voter_keys.append(key)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'voterKeys': voter_keys
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/results')
@admin_required
def admin_results():
    elections_data = {}
    elections = Election.query.all()
    
    for election in elections:
        total_voters = len(election.voter_keys)
        votes_cast = Vote.query.filter_by(election_id=election.id).count()
        turnout_percentage = (votes_cast / total_voters * 100) if total_voters > 0 else 0
        
        candidates_data = []
        for candidate in election.candidates:
            vote_percentage = (candidate.votes / votes_cast * 100) if votes_cast > 0 else 0
            candidates_data.append({
                'name': candidate.name,
                'votes': candidate.votes,
                'percentage': round(vote_percentage, 1)
            })
        
        elections_data[election.title] = {
            'position': election.position,
            'total_voters': total_voters,
            'votes_cast': votes_cast,
            'turnout_percentage': round(turnout_percentage, 1),
            'candidates': candidates_data
        }
    
    return render_template('admin/results.html', elections=elections_data)

@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        voter_key = request.form.get('voterKey')
        voter = VoterKey.query.filter_by(key=voter_key, is_used=False).first()
        
        if voter:
            session['voter_key_id'] = voter.id
            session['election_id'] = voter.election_id
            return redirect(url_for('vote'))
        flash('Invalid or used voter key')
    return render_template('voter/login.html')

@app.route('/voter/vote', methods=['GET'])
@voter_required
def vote():
    election = Election.query.get_or_404(session['election_id'])
    if not election.is_active:
        flash('This election is no longer active')
        return redirect(url_for('index'))
    return render_template('voter/vote.html', election=election, candidates=election.candidates)

@app.route('/voter/cast-vote', methods=['POST'])
@voter_required
def cast_vote():
    try:
        data = request.json
        voter_key = VoterKey.query.get(session['voter_key_id'])
        
        if voter_key.is_used:
            return jsonify({'error': 'Vote already cast'}), 400
        
        election = Election.query.get(session['election_id'])
        if not election.is_active:
            return jsonify({'error': 'Election is no longer active'}), 400
        
        # Record vote
        vote = Vote(
            election_id=session['election_id'],
            voter_key_id=voter_key.id,
            candidate_id=data['candidateId']
        )
        db.session.add(vote)
        
        # Mark voter key as used
        voter_key.is_used = True
        
        # Increment candidate votes
        candidate = Candidate.query.get(data['candidateId'])
        candidate.votes += 1
        
        db.session.commit()
        
        # Clear voter session
        session.pop('voter_key_id', None)
        session.pop('election_id', None)
        
        return jsonify({'success': True, 'message': 'Vote cast successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
