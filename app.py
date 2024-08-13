from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elo_ranking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=1000)
    history = db.Column(db.String(5000), nullable=False, default='1000')

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    elo_change_winner = db.Column(db.Integer, nullable=False)
    elo_change_loser = db.Column(db.Integer, nullable=False)

    player1 = db.relationship('Player', foreign_keys=[player1_id])
    player2 = db.relationship('Player', foreign_keys=[player2_id])
    winner = db.relationship('Player', foreign_keys=[winner_id])

@app.route('/')
def index():
    # Get all players sorted by rating
    players = Player.query.order_by(Player.rating.desc()).all()

    # Get the last 5 matches
    last_5_matches = Match.query.order_by(Match.id.desc()).limit(5).all()

    # Create ELO chart
    elo_chart = generate_elo_chart(players)

    return render_template('index.html', players=players, matches=last_5_matches, elo_chart=elo_chart)

def calculate_elo(winner, loser, k=32):
    expected_winner = 1 / (1 + 10 ** ((loser.rating - winner.rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner.rating - loser.rating) / 400))

    winner_new_rating = round(winner.rating + k * (1 - expected_winner))
    loser_new_rating = round(loser.rating + k * (0 - expected_loser))

    elo_change_winner = winner_new_rating - winner.rating
    elo_change_loser = loser_new_rating - loser.rating

    # Update players' ratings and history
    winner.rating = winner_new_rating
    loser.rating = loser_new_rating

    winner.history += f",{winner_new_rating}"
    loser.history += f",{loser_new_rating}"

    db.session.commit()

    return elo_change_winner, elo_change_loser

@app.route('/add_match', methods=['POST'])
def add_match():
    player1_name = request.form['player1']
    player2_name = request.form['player2']
    winner_name = request.form['winner']

    player1 = Player.query.filter_by(name=player1_name).first()
    player2 = Player.query.filter_by(name=player2_name).first()
    winner = Player.query.filter_by(name=winner_name).first()

    if winner == player1:
        loser = player2
    else:
        loser = player1

    elo_change_winner, elo_change_loser = calculate_elo(winner, loser)

    # Record the match
    match = Match(player1=player1, player2=player2, winner=winner,
                  elo_change_winner=elo_change_winner, elo_change_loser=elo_change_loser)
    db.session.add(match)
    db.session.commit()

    return redirect(url_for('index'))

# def generate_elo_chart(players):
#     plt.figure(figsize=(7, 4))  # Adjust the size for better fit
    
#     for player in players:
#         history = list(map(int, player.history.split(',')))
#         plt.plot(range(1, len(history) + 1), history, label=player.name)
    
#     plt.xlabel('Games Played')
#     plt.ylabel('ELO Rating')
#     plt.title('ELO Rating Over Time')
#     plt.legend()

#     img = io.BytesIO()
#     plt.savefig(img, format='png')
#     img.seek(0)
#     plt.close()
#     return base64.b64encode(img.getvalue()).decode()

def generate_elo_chart(players):
    plt.figure(figsize=(7, 4))  # Adjust the size for better fit

    # Use a custom dark theme with a slightly lighter background
    # plt.style.use('grey_background')
    plt.style.use('ggplot')
    plt.rcParams.update({
        'axes.facecolor': '#2c2f33',
        'axes.edgecolor': '#444444',
        'axes.labelcolor': '#ffffff',
        'xtick.color': '#ffffff',
        'ytick.color': '#ffffff',
        'figure.facecolor': '#23272a',
        'grid.color': '#555555',
    })

    for player in players:
        history = list(map(int, player.history.split(',')))
        plt.plot(range(1, len(history) + 1), history, label=player.name)

        # Adding marker only for the last data point
        plt.plot(len(history), history[-1], 'o', markersize=8)  # Marker for last data point

    plt.xlabel('Games Played', color='white')
    plt.ylabel('ELO Rating', color='white')
    plt.title('ELO Rating Over Time', color='white')

    plt.xticks(color='white')
    plt.yticks(color='white')

    plt.legend(facecolor='#dae5f5', edgecolor='white', loc='best')  # Dark legend background with white borders
    plt.grid(color='gray', linestyle='--', linewidth=0.5)  # Light grid lines

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')  # Adjust to fit the content nicely
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if Player.query.count() == 0:
            initial_players = ["Tarald", "Lars", "Aleksandra", "Jonas", "Dan Ove"]
            for player_name in initial_players:
                player = Player(name=player_name)
                db.session.add(player)
            db.session.commit()

    app.run(debug=True)
