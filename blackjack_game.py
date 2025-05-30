import random
import sqlite3
from collections import defaultdict
import os
from dotenv import load_dotenv
from google import generativeai as genai  # Gemini API

class BlackjackGame:
    def __init__(self, db_path="blackjack.db"):
        self.active_games = {}  # Store games by channel name
        self.player_hands = defaultdict(list)  # Store player hands by username
        self.dealer_hands = {}  # Store dealer hands by channel
        self.deck = {}  # Store deck by channel
        self.game_status = {}  # Store game status by channel
        self.player_bets = {}  # Store player bets
        self.pot = {}  # Store the pot for each channel
        self.players = {}  # Store players by channel
        
        # Set up database
        self.db_path = db_path
        self.setup_database()

        load_dotenv()
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        
    def setup_database(self):
        """Create the database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table to store chip balances
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            chips INTEGER DEFAULT 1000,
            total_games INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            pushes INTEGER DEFAULT 0
        )
        ''')
        
        # Create transaction history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount INTEGER,
            type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user_chips(self, username):
        """Get a user's chip balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT chips FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result is None:
            # New user - create with default balance
            default_chips = 1000
            cursor.execute(
                "INSERT INTO users (username, chips) VALUES (?, ?)",
                (username, default_chips)
            )
            conn.commit()
            chips = default_chips
        else:
            chips = result[0]
        
        conn.close()
        return chips
    
    def update_user_chips(self, username, amount, transaction_type):
        """Update a user's chip balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current balance
        current_chips = self.get_user_chips(username)
        new_balance = current_chips + amount
        
        # Update balance
        cursor.execute(
            "UPDATE users SET chips = ? WHERE username = ?",
            (new_balance, username)
        )
        
        # Record transaction
        cursor.execute(
            "INSERT INTO transactions (username, amount, type) VALUES (?, ?, ?)",
            (username, amount, transaction_type)
        )
        
        conn.commit()
        conn.close()
        return new_balance
    
    def update_stats(self, username, result):
        """Update user statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Increment total games
        cursor.execute(
            "UPDATE users SET total_games = total_games + 1 WHERE username = ?",
            (username,)
        )
        
        # Update specific result counter
        if result == "win":
            cursor.execute(
                "UPDATE users SET wins = wins + 1 WHERE username = ?",
                (username,)
            )
        elif result == "loss":
            cursor.execute(
                "UPDATE users SET losses = losses + 1 WHERE username = ?",
                (username,)
            )
        elif result == "push":
            cursor.execute(
                "UPDATE users SET pushes = pushes + 1 WHERE username = ?",
                (username,)
            )
        
        conn.commit()
        conn.close()
    
    def get_leaderboard(self, limit=5):
        """Get the top players by chip count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT username, chips, wins, losses FROM users ORDER BY chips DESC LIMIT ?",
            (limit,)
        )
        
        leaderboard = cursor.fetchall()
        conn.close()
        return leaderboard
    
    def create_deck(self):
        """Create a new shuffled deck of cards"""
        suits = ['♥', '♦', '♣', '♠']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(value, suit) for suit in suits for value in values]
        random.shuffle(deck)
        return deck
    
    def card_value(self, card):
        """Calculate the value of a card"""
        value, _ = card
        if value in ['J', 'Q', 'K']:
            return 10
        elif value == 'A':
            return 11  # Aces are initially 11, can be reduced to 1 if needed
        else:
            return int(value)
    
    def hand_value(self, hand):
        """Calculate the value of a hand, accounting for aces"""
        value = sum(self.card_value(card) for card in hand)
        # Adjust for aces if needed
        aces = sum(1 for card in hand if card[0] == 'A')
        while value > 21 and aces > 0:
            value -= 10  # Convert an ace from 11 to 1
            aces -= 1
        return value
    
    def format_card(self, card):
        """Format a card for display"""
        value, suit = card
        return f"{value}{suit}"
    
    def format_hand(self, hand):
        """Format a hand for display"""
        return " ".join(self.format_card(card) for card in hand)
    
    def start_game(self, channel):
        """Start a new blackjack game in the channel"""
        if channel in self.active_games and self.active_games[channel]:
            return "A game is already in progress!"
        
        self.active_games[channel] = True
        self.deck[channel] = self.create_deck()
        self.dealer_hands[channel] = []
        self.player_hands.clear()
        self.player_bets.clear()
        self.pot[channel] = 0  # Initialize the pot for the channel
        self.game_status[channel] = "betting"
        
        return "🎲 Blackjack game started! Type '~bet [amount]' to join!"
    
    def join_game(self, channel, username, bet=10):
        """Player joins the game with a bet"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress. Type '~blackjack' to start a game!"
        
        if self.game_status[channel] != "betting":
            return "Betting period is over! Wait for the next game."
        
        if username in self.player_hands:
            return f"{username}, you're already in this game!"
        
        # Check if player has enough chips
        current_chips = self.get_user_chips(username)
        if bet <= 0:
            return f"{username}, you must bet at least 1 chip!"
        
        if current_chips < bet:
            return f"Sorry {username}, you only have {current_chips} chips. Bet a smaller amount."
        
        # Deduct bet from player's balance
        self.update_user_chips(username, -bet, "bet")
        
        # Store the bet
        self.player_bets[username] = bet
        
        # Add the bet to the pot
        self.pot[channel] += bet
        
        # Deal initial cards
        self.player_hands[username] = [self.deck[channel].pop(), self.deck[channel].pop()]
        
        hand_value = self.hand_value(self.player_hands[username])
        return f"{username} joins with {bet} chips! Your cards: {self.format_hand(self.player_hands[username])} ({hand_value}) | Balance: {current_chips - bet} chips"
    
    def start_dealing(self, channel):
        """Start the dealing phase after betting is complete"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if len(self.player_hands) == 0:
            self.active_games[channel] = False
            return "No players joined! Game cancelled."
        
        self.game_status[channel] = "playing"
        
        # Deal dealer's cards
        self.dealer_hands[channel] = [self.deck[channel].pop(), self.deck[channel].pop()]
        dealer_card = self.format_card(self.dealer_hands[channel][0])
        
        return f"Dealing begins! Dealer shows: {dealer_card} ?️"
    
    def hit(self, channel, username):
        """Player requests another card"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if self.game_status[channel] != "playing":
            return "It's not time to hit yet!"
        
        if username not in self.player_hands:
            return f"{username}, you're not in this game!"
        
        # Deal a new card
        self.player_hands[username].append(self.deck[channel].pop())
        hand = self.player_hands[username]
        hand_value = self.hand_value(hand)
        
        if hand_value > 21:
            # Player busts - update stats
            self.update_stats(username, "loss")
            result = f"{username} busts with {hand_value}! Cards: {self.format_hand(hand)}"
        else:
            result = f"{username} hits and gets {self.format_card(hand[-1])}. " \
                    f"Hand: {self.format_hand(hand)} ({hand_value})"
        
        return result
    
    def winning_response(self, channel, message):
        user_input = message
        suzu_prompt = os.getenv("SUZU_PROMPT_2")
        winning_prompt = suzu_prompt + f""" Craft a single chat message only no additional text to tell the chat who won the blackjack game, and here is the text with that information."""

        if not user_input:
            return "No input provided"
        
        try:
            # Gemini API Call
            response = self.model.generate_content([winning_prompt, user_input])
            ai_response = response.text.strip()
            return ai_response
        except Exception as e:
            print(f"Error in winning_response generation: {str(e)}")
            # Fallback to a default response
            fallback_response = user_input
            return fallback_response

    def stand(self, channel, username):
        """Player stands with current hand"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if self.game_status[channel] != "playing":
            return "It's not time to stand yet!"
        
        if username not in self.player_hands:
            return f"{username}, you're not in this game!"
        
        hand = self.player_hands[username]
        hand_value = self.hand_value(hand)
        
        return f"{username} stands with {hand_value}. Cards: {self.format_hand(hand)}"
    
    def dealer_play(self, channel):
        """Dealer plays their hand"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if self.game_status[channel] != "playing":
            return "It's not time for the dealer to play yet!"
        
        dealer_hand = self.dealer_hands[channel]
        
        # Dealer hits until they have at least 17
        while self.hand_value(dealer_hand) < 17:
            dealer_hand.append(self.deck[channel].pop())
        
        dealer_value = self.hand_value(dealer_hand)
        dealer_busted = dealer_value > 21
        
        # Determine results for all players
        results = [f"Dealer has: {self.format_hand(dealer_hand)} ({dealer_value})"]
        
        if dealer_busted:
            results.append("Dealer busts!")
        
        winners = []
        for player, hand in self.player_hands.items():
            player_value = self.hand_value(hand)
            
            if player_value > 21:
                # Player already busted
                results.append(f"{player} busted with {player_value}")
            elif dealer_busted or player_value > dealer_value:
                # Player wins
                winners.append(player)
                results.append(f"{player} wins with {player_value}!")
            elif player_value == dealer_value:
                # Push
                results.append(f"{player} pushes with {player_value}.")
            else:
                # Player loses
                results.append(f"{player} loses with {player_value} vs dealer's {dealer_value}.")
        
        # Handle pot distribution
        if len(winners) == 1:
            # Single winner takes the entire pot
            winner = winners[0]
            new_balance = self.update_user_chips(winner, self.pot[channel], "win")
            results.append(f"{winner} takes the pot of {self.pot[channel]} chips! New balance: {new_balance} chips")
        elif len(winners) > 1:
            # Split the pot among winners, ensuring each gets their original bet back
            total_bets = sum(self.player_bets[player] for player in winners)
            remaining_pot = self.pot[channel] - total_bets
            
            if remaining_pot < 0:
                remaining_pot = 0
            
            split_amount = remaining_pot // len(winners)
            for winner in winners:
                original_bet = self.player_bets[winner]
                payout = original_bet + split_amount
                new_balance = self.update_user_chips(winner, payout, "win")
                results.append(f"{winner} wins {payout} chips (original bet + split)! New balance: {new_balance} chips")
        elif len(self.player_hands) == 1 and "suzu" in self.player_hands:
            player = list(self.player_hands.keys())[0]
            split_amount = self.pot[channel] // 2
            new_balance = self.update_user_chips(player, split_amount, "split")
            results.append(f"Only {player} and Suzu played. {player} takes half the pot: {split_amount} chips! New balance: {new_balance} chips")
        else:
            # No winners, pot remains with the dealer
            results.append("No winners. The pot remains with the dealer.")
        
        # # Special case: Only one player and Suzu
        # if len(self.player_hands) == 1 and "suzu" in self.player_hands:
        #     player = list(self.player_hands.keys())[0]
        #     split_amount = self.pot[channel] // 2
        #     new_balance = self.update_user_chips(player, split_amount, "split")
        #     results.append(f"Only {player} and Suzu played. {player} takes half the pot: {split_amount} chips! New balance: {new_balance} chips")
        
        # End the game
        self.active_games[channel] = False
        
        winning_message = self.winning_response(channel, "\n".join(results))
        return winning_message
    
    def get_balance(self, username):
        """Get a user's current balance"""
        chips = self.get_user_chips(username)
        return f"{username}'s balance: {chips} chips"
    
    def add_chips(self, username, amount):
        """Add chips to a user's balance (admin function)"""
        if amount <= 0:
            return f"Amount must be positive"
        
        new_balance = self.update_user_chips(username, amount, "admin_add")
        return f"Added {amount} chips to {username}'s balance. New balance: {new_balance} chips"
    
    def get_stats(self, username):
        """Get a user's statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT chips, total_games, wins, losses, pushes FROM users WHERE username = ?",
            (username,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"{username} hasn't played any games yet."
        
        chips, total_games, wins, losses, pushes = result
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        return f"{username}'s Stats: {chips} chips | Games: {total_games} | Wins: {wins} | Losses: {losses} | Pushes: {pushes} | Win Rate: {win_rate:.1f}%"

    def double_down(self, channel, username):
        """Double the bet and take exactly one more card"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if self.game_status[channel] != "playing":
            return "It's not time to double down yet!"
        
        if username not in self.player_hands:
            return f"{username}, you're not in this game!"
        
        # Check if player has already hit (can only double down on initial hand)
        if len(self.player_hands[username]) > 2:
            return f"{username}, you can only double down on your initial hand!"
        
        # Check if player has enough chips for the additional bet
        current_bet = self.player_bets.get(username, 10)
        current_chips = self.get_user_chips(username)
        
        if current_chips < current_bet:
            return f"Sorry {username}, you need {current_bet} more chips to double down."
        
        # Deduct additional bet
        self.update_user_chips(username, -current_bet, "double_down")
        
        # Double the bet
        self.player_bets[username] = current_bet * 2
        
        # Deal exactly one more card
        self.player_hands[username].append(self.deck[channel].pop())
        hand = self.player_hands[username]
        hand_value = self.hand_value(hand)
        
        result = f"{username} doubles down to {current_bet * 2} chips and gets {self.format_card(hand[-1])}. "
        
        if hand_value > 21:
            # Player busts
            self.update_stats(username, "loss")
            result += f"Busts with {hand_value}! Cards: {self.format_hand(hand)}"
        else:
            result += f"Final hand: {self.format_hand(hand)} ({hand_value})"
        
        return result

    def insurance(self, channel, username):
        """Place an insurance bet against dealer blackjack"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        if self.game_status[channel] != "playing":
            return "It's not time for insurance!"
        
        if username not in self.player_hands:
            return f"{username}, you're not in this game!"
        
        # Check if dealer's up card is an Ace
        dealer_up_card = self.dealer_hands[channel][0]
        if dealer_up_card[0] != 'A':
            return f"Insurance is only available when the dealer shows an Ace!"
        
        # Check if player already has insurance
        if f"{username}_insurance" in self.player_bets:
            return f"{username}, you already have insurance!"
        
        # Insurance costs half the original bet
        original_bet = self.player_bets.get(username, 10)
        insurance_cost = original_bet // 2
        
        # Check if player has enough chips
        current_chips = self.get_user_chips(username)
        if current_chips < insurance_cost:
            return f"Sorry {username}, you need {insurance_cost} chips for insurance."
        
        # Deduct insurance cost
        self.update_user_chips(username, -insurance_cost, "insurance")
        
        # Store insurance bet
        self.player_bets[f"{username}_insurance"] = insurance_cost
        
        return f"{username} places an insurance bet of {insurance_cost} chips."

    def check_dealer_blackjack(self, channel):
        """Check if dealer has blackjack and process insurance bets"""
        if channel not in self.active_games or not self.active_games[channel]:
            return "No game in progress!"
        
        dealer_hand = self.dealer_hands[channel]
        dealer_has_blackjack = len(dealer_hand) == 2 and self.hand_value(dealer_hand) == 21
        
        results = []
        
        if dealer_has_blackjack:
            results.append(f"Dealer has blackjack! {self.format_hand(dealer_hand)}")
            
            # Process insurance bets
            for player in list(self.player_hands.keys()):
                insurance_key = f"{player}_insurance"
                
                if insurance_key in self.player_bets:
                    # Insurance pays 2:1
                    insurance_bet = self.player_bets[insurance_key]
                    insurance_payout = insurance_bet * 3  # Original bet + 2x winnings
                    
                    self.update_user_chips(player, insurance_payout, "insurance_win")
                    results.append(f"{player} wins {insurance_bet * 2} chips on insurance! Total payout: {insurance_payout}")
                
                # Player loses main bet unless they also have blackjack
                player_hand = self.player_hands[player]
                player_has_blackjack = len(player_hand) == 2 and self.hand_value(player_hand) == 21
                
                if player_has_blackjack:
                    # Push on blackjack vs blackjack
                    original_bet = self.player_bets[player]
                    self.update_user_chips(player, original_bet, "push")
                    self.update_stats(player, "push")
                    results.append(f"{player} pushes with blackjack vs dealer blackjack.")
                else:
                    # Player loses
                    self.update_stats(player, "loss")
                    results.append(f"{player} loses to dealer blackjack.")
            
            # End the game
            self.active_games[channel] = False
        else:
            results.append("Dealer does not have blackjack. Game continues!")
            
            # Insurance bets lose
            for player in list(self.player_hands.keys()):
                insurance_key = f"{player}_insurance"
                if insurance_key in self.player_bets:
                    results.append(f"{player} loses their insurance bet.")
        
        return "\n".join(results)