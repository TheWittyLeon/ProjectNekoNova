import sqlite3
import random
import re
import twitchio
import json


class RPGHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self.active_battle = None  # Track the current battle
        self.initiative_order = []  # Track initiative order (players and monster)
        self.player_actions = {}  # Track player actions

    def get_user_tokens(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT chips, level, xp, strength, dexterity, intelligence, vitality, hp, max_hp, inventory FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                "chips": result[0],
                "level": result[1],
                "xp": result[2],
                "strength": result[3],
                "dexterity": result[4],
                "intelligence": result[5],  # Fixed indexing
                "vitality": result[6],      # Fixed indexing
                "hp": result[7],            # Fixed indexing
                "max_hp": result[8],        # Fixed indexing
            }
        else:
            return {"chips": 0, "level": 1, "xp": 0}

    def update_user_tokens(self, username, amount):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET chips = chips + ? WHERE username = ?", (amount, username))
        conn.commit()
        conn.close()

    def get_item_info(self, item_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cost, effect, level_required FROM items WHERE name = ?", (item_name,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"cost": result[0], "effect": result[1], "level_required": result[2]}
        else:
            return None

    def buy_item(self, username, item_name, quantity=1):
        """Allow a user to buy an item and add it to their inventory."""
        item_info = self.get_item_info(item_name)
        if not item_info:
            return "That item doesn't exist!"

        user_data = self.get_user_tokens(username)
        user_tokens = user_data["chips"]
        user_level = user_data["level"]

        total_cost = item_info["cost"] * quantity

        if user_tokens < total_cost:
            return f"You don't have enough tokens! You need {total_cost} tokens to buy {quantity} {item_name}(s)."

        if user_level < item_info["level_required"]:
            return f"You must be level {item_info['level_required']} to buy this item!"

        # Deduct the total cost from the user's tokens
        self.update_user_tokens(username, -total_cost)

        # Add the item(s) to the user's inventory
        self.add_item_to_inventory(username, item_name, quantity)

        return f"{username} bought {quantity} {item_name}(s) for {total_cost} tokens!"

    def roll_dice(self, dice_notation):
        match = re.match(r'(\d+)d(\d+)', dice_notation)
        if match:
            num_dice = int(match.group(1))
            sides = int(match.group(2))
            results = [random.randint(1, sides) for _ in range(num_dice)]
            return sum(results)
        else:
            return 0

    def get_user_stats(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT chips, level, xp, hp, max_hp FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return f"{username}'s Stats: Chips: {result[0]}, Level: {result[1]}, XP: {result[2], cur}, HP: {result[3]}/{result[4]}"
        else:
            return f"{username} has no stats yet."

    def use_item(self, username, item_name):
        item_info = self.get_item_info(item_name)
        if not item_info:
            return "That item doesn't exist!"

        user_data = self.get_user_tokens(username)
        user_level = user_data["level"]

        if user_level < item_info["level_required"]:
            return f"You must be level {item_info['level_required']} to use this item!"

        # Implement the effect of the item (this is a placeholder)
        effect = item_info["effect"]
        return f"{username} used {item_name}! Effect: {effect}"

    def gain_xp(self, username, xp_amount):
        user_data = self.get_user_tokens(username)
        new_xp = user_data["xp"]
        new_level = user_data["level"]
        chips = user_data["chips"]

        print(f"XP before: {new_xp}, Level before: {new_level}, Chips before: {chips}")

        if xp_amount < 0:
            return "You can't gain negative XP!"
        elif xp_amount == 0:
            return f"{username} gained no XP."
        elif xp_amount > chips:
            return f"{username} you don't have enough chips to gain that much XP!"
        else: # Add XP
            self.update_user_tokens(username, -xp_amount)
            new_xp += xp_amount

        # Level up logic
        xp_for_next_level = new_level * 1000  # Example: 100 XP per level
        while new_xp >= xp_for_next_level:
            new_xp -= xp_for_next_level
            new_level += 1
            xp_for_next_level = new_level * 1000

        print(f"XP after: {new_xp}, Level after: {new_level}, Chips after: {chips}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET xp = ?, level = ? WHERE username = ?", (new_xp, new_level, username))
        conn.commit()
        conn.close()

        return f"{username} gained {xp_amount} XP and is now level {new_level} with {new_xp} XP."

    def get_user_xp(self, username):
        user_data = self.get_user_tokens(username)
        return f"{username} is level {user_data['level']} with {user_data['xp']} XP."

    def calculate_modifier(self, ability_score):
        """Calculate the ability modifier based on the ability score."""
        return (ability_score - 10) // 2

    def roll_initiative(self, dexterity_score):
        """Roll initiative using a d20 and the Dexterity modifier."""
        dexterity_modifier = self.calculate_modifier(dexterity_score)
        return max(1, random.randint(1, 20) + dexterity_modifier)  # Ensure initiative is at least 1

    def spawn_monster(self, challenge_rating=None):
        """Spawn a monster from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Select a monster based on challenge rating or randomly
        if challenge_rating:
            cursor.execute("SELECT * FROM monsters WHERE challenge_rating = ?", (challenge_rating,))
        else:
            cursor.execute("SELECT * FROM monsters ORDER BY RANDOM() LIMIT 1")

        monster = cursor.fetchone()
        conn.close()

        if not monster:
            return None

        # Parse monster stats
        (
            monster_id, name, hp_range, hp_mod, dmg_range, dmg_mod, special, trigger, tokens, cr,
            strength, dexterity, constitution, intelligence, wisdom, charisma, armor_class
        ) = monster

        # Handle missing `hp_modifier` and `damage_modifier` by assigning default values
        if hp_mod is None:
            print("Error: hp_mod is missing, defaulting to 0.")
            hp_mod = 0
        if dmg_mod is None:
            print("Error: dmg_mod is missing, defaulting to 0.")
            dmg_mod = 0

        hp = self.roll_dice(hp_range) + hp_mod
        damage = self.roll_dice(dmg_range) + dmg_mod

        # Return monster stats
        return {
            "id": monster_id,
            "name": name,
            "hp": hp,
            "damage": damage,
            "dexterity": dexterity,
            "armor_class": armor_class,
            "special": special,
            "trigger": trigger,
            "tokens": tokens,
            "challenge_rating": cr,
        }

    def start_battle(self, channel, monster):
        """Start a battle with a spawned monster."""
        if self.active_battle:
            return "A battle is already in progress!"

        # Roll initiative for the monster
        monster_initiative = self.roll_initiative(monster["dexterity"])

        self.active_battle = {
            "channel": channel,
            "monster": monster,
            "monster_hp": monster["hp"],
            "players": [],
        }
        self.initiative_order = [(monster["name"], monster_initiative)]  # Add monster to initiative order
        self.player_actions = {}

        return f"A wild {monster['name']} has appeared with {monster['hp']} HP! Type `~joinbattle` to join the fight!"

    def join_battle(self, username):
        """Allow a player to join the battle."""
        if not self.active_battle:
            return "No battle is currently active!"

        if username in self.active_battle["players"]:
            return f"{username}, you are already in the battle!"

        # Roll initiative for the player
        player_data = self.get_user_tokens(username)
        player_dexterity = player_data.get("dexterity", 10)  # Default to 10 if not tracked
        initiative = self.roll_initiative(player_dexterity)

        self.active_battle["players"].append(username)
        self.initiative_order.append((username, initiative))
        self.initiative_order.sort(key=lambda x: x[1], reverse=True)  # Sort by initiative

        return f"{username} has joined the battle with an initiative roll of {initiative}!"

    def get_next_initiative(self):
        """Get the next entity in the initiative order."""
        if not self.active_battle or not self.initiative_order:
            return None  # No active battle or empty initiative order

        # Peek at the next entity in the initiative order
        next_entity = self.initiative_order[0]

        if next_entity[0] == self.active_battle["monster"]["name"]:
            return ("monster", next_entity[0])  # Return monster type and name
        else:
            return ("user", next_entity[0])  # Return user type and username

    def get_inventory(self, username):
        """Retrieve the user's inventory."""
        user_data = self.get_user_tokens(username)
        inventory = user_data.get("inventory", [])
        return inventory

    def add_item_to_inventory(self, username, item_name):
        """Add an item to the user's inventory."""
        user_data = self.get_user_tokens(username)
        inventory = user_data.get("inventory", [])
        inventory.append(item_name)
        user_data["inventory"] = inventory
        self.update_user_tokens(username, user_data)
        return f"{username}, you have added {item_name} to your inventory."

    def check_inventory(self, username, item_name):
        """Check if a user has a specific item in their inventory."""
        inventory = self.get_inventory(username)
        return item_name in inventory

    def potion_heal(self, username, potion_name):
        """Heal the user with a potion."""
        user_data = self.get_user_tokens(username)
        if not user_data:
            return "User not found."
        if potion_name not in user_data.get("inventory", []):
            return "You don't have that potion!"
        else:
            # Remove the potion from the inventory
            user_data["inventory"].remove(potion_name)
            # Heal the user (you'll need to implement the healing logic)
            if potion_name == "small potion":
                heal_amount = 10
            elif potion_name == "medium potion":
                heal_amount = 20
            elif potion_name == "large potion":
                heal_amount = 30
            user_data["hp"] = min(user_data["hp"] + heal_amount, user_data["max_hp"])
            # Update the user's HP in the database
            self.update_user_tokens(username, user_data)
            # For example, you could add a healing function here
            return f"{username}, you have used a {potion_name} and healed for {heal_amount} HP!"

    

    def update_initiative_order(self):
        """Update the initiative order based on the current state of the battle."""
        if not self.active_battle:
            print("No active battle to update initiative order.")  # Debug print
        else:
            current_turn = self.initiative_order.pop(0)
            self.initiative_order.append(current_turn)

    def take_turn(self):
        """Process the next turn in the initiative order."""
        if not self.active_battle or not self.initiative_order:
            return "No battle is currently active!"

        print(f"Initiative order before turn: {self.initiative_order}")  # Debug print
        # Get the next entity in the initiative order
        current_turn = self.initiative_order.pop(0)

        # Add the current entity back to the end of the initiative order
        self.initiative_order.append(current_turn)
        print(f"Current turn: {current_turn}")  # Debug print
        print(f"Initiative order: {self.initiative_order}")  # Debug print

        if current_turn[0] == self.active_battle["monster"]["name"]:
            # Monster's turn
            result = self.monster_attack()
            # Automatically proceed to the next turn after the monster attacks
            if self.active_battle:  # Ensure the battle is still active
                next_turn_result = self.take_turn()
                return f"{result}\n{next_turn_result}"[:500]  # Ensure the response is within 500 characters
            return result
        else:
            # Player's turn
            username = current_turn[0]
            return f"It's {username}'s turn! Use `~attack` to attack the monster."

    def player_attack(self, username):
        """Handle a player's attack on the monster."""
        if not self.active_battle:
            return "No battle is currently active!"

        # Ensure initiative order is initialized
        if not isinstance(self.initiative_order, list) or not self.initiative_order:
            return "The initiative order is not properly set!"

        # Check if it's the player's turn
        if not self.initiative_order or self.initiative_order[0][0] != username:
            return f"It's not your turn, {username}!"

        if username not in self.active_battle["players"]:
            return f"{username}, you are not in the battle!"

        # Roll for damage
        damage = random.randint(1, 6)  # Example: 1d6 damage
        self.active_battle["monster_hp"] -= damage

        if self.active_battle["monster_hp"] <= 0:
            monster_name = self.active_battle["monster"]["name"]
            tokens = self.active_battle["monster"]["tokens"]
            players = self.active_battle["players"]  # Save players before ending the battle
            self.end_battle()
            for player in players:
                self.update_user_tokens(player, tokens)  # Add tokens to each player
            # Return the result of the attack
            return f"{username} dealt {damage} damage and defeated the {monster_name}! Everyone gains {tokens} tokens!"

        # Return the result of the attack
        return f"{username} dealt {damage} damage! The monster has {self.active_battle['monster_hp']} HP remaining."

    def monster_attack(self):
        """Handle the monster's attack on a random player."""
        if not self.active_battle:
            return "No battle is currently active!"

        if not self.active_battle["players"]:
            return "No players are in the battle!"

        # Choose a random player to attack
        target = random.choice(self.active_battle["players"])
        damage = self.active_battle["monster"]["damage"]

        # Fetch the target player's current HP
        user_data = self.get_user_tokens(target)
        current_hp = user_data["hp"]
        print(f"Current HP of {target}: {current_hp}")  # Debug print
        print(f"Damage dealt by monster: {damage}")  # Debug print

        # Apply damage to the player
        new_hp = max(0, current_hp - damage)  # Ensure HP doesn't go below 0
        print(f"New HP of {target}: {new_hp}")  # Debug print
        next_turn = self.get_next_initiative()
        print(f"Next turn: {next_turn}")  # Debug print

        # Update the player's HP in the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hp = ? WHERE username = ?", (new_hp, target))
        conn.commit()
        conn.close()

        self.update_initiative_order()  # Update initiative order for the next turn 

        # Check if the player is defeated
        if new_hp == 0:
            self.active_battle["players"].remove(target)
            defeat_message = f"{target} has been defeated by the monster!"

            # If no players are left, end the battle
            if not self.active_battle["players"]:
                self.end_battle()
                return f"The monster attacked {target} for {damage} damage! {defeat_message} The battle is over. The monster wins!"

            return f"The monster attacked {target} for {damage} damage! {defeat_message}"

        # Return the result of the attack
        return f"The monster attacked {target} for {damage} damage! {target} has {new_hp} HP remaining."

    def end_battle(self):
        """End the current battle."""
        self.active_battle = None
        self.initiative_order = []
        self.player_actions = {}

    def start_battle_trigger(self):
        """Start the battle after enough players have joined or a timeout occurs."""
        if not self.active_battle:
            return "No battle is currently active!"

        # Check if a monster has been spawned
        if not self.active_battle.get("monster"):
            return "No monster has been spawned for the battle!"

        # Check if players have joined the battle
        if len(self.active_battle["players"]) < 1:
            return "Not enough players have joined the battle! At least one player is required to start."

        # Sort the initiative order
        self.initiative_order.sort(key=lambda x: x[1], reverse=True)

        # Announce the turn order
        turn_order = ", ".join([f"{entity[0]} (Initiative: {entity[1]})" for entity in self.initiative_order])
        return f"The battle begins! Turn order: {turn_order}"

    def heal_player(self, username, heal_amount=None):
        """Heal a player by a specified amount or to full health if no amount is given."""
        if not self.active_battle:
            return "No battle is currently active!"

        # Fetch the player's current HP and max HP
        user_data = self.get_user_tokens(username)
        current_hp = user_data["hp"]
        max_hp = user_data["max_hp"]

        if current_hp >= max_hp:
            return f"{username} is already at full health!"

        # If no heal amount is specified, heal to max HP
        if heal_amount is None:
            heal_amount = max_hp - current_hp

        # Calculate the new HP after healing
        new_hp = min(current_hp + heal_amount, max_hp)  # Ensure HP doesn't exceed max HP

        # Update the player's HP in the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hp = ? WHERE username = ?", (new_hp, username))
        conn.commit()
        conn.close()

        return f"{username} has been healed for {heal_amount} HP and now has {new_hp}/{max_hp} HP!"

    import json

    # Add an item to the user's inventory
    def add_item_to_inventory(self, username, item_name, amount=1):
        """Add an item to the user's inventory."""
        user_data = self.get_user_tokens(username)
        inventory = json.loads(user_data.get("inventory", "{}"))  # Load inventory as a dictionary

        # Update the item quantity
        if item_name in inventory:
            inventory[item_name] += amount
        else:
            inventory[item_name] = amount

        # Save the updated inventory back to the database
        inventory_json = json.dumps(inventory)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET inventory = ? WHERE username = ?", (inventory_json, username))
        conn.commit()
        conn.close()

        return f"{username} now has {inventory[item_name]} {item_name}(s) in their inventory."

    # Remove an item from the user's inventory
    def remove_item_from_inventory(self, username, item_name, amount=1):
        """Remove an item from the user's inventory."""
        user_data = self.get_user_tokens(username)
        inventory = json.loads(user_data.get("inventory", "{}"))  # Load inventory as a dictionary

        if item_name not in inventory or inventory[item_name] < amount:
            return f"{username} does not have enough {item_name}(s) to remove."

        # Update the item quantity
        inventory[item_name] -= amount
        if inventory[item_name] <= 0:
            del inventory[item_name]  # Remove the item if the quantity is zero

        # Save the updated inventory back to the database
        inventory_json = json.dumps(inventory)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET inventory = ? WHERE username = ?", (inventory_json, username))
        conn.commit()
        conn.close()

        return f"{username} now has {inventory.get(item_name, 0)} {item_name}(s) in their inventory."
    
    #Get the user's inventory
    def get_inventory(self, username):
        """Retrieve the user's inventory."""
        user_data = self.get_user_tokens(username)
        inventory = json.loads(user_data.get("inventory", "{}"))  # Load inventory as a dictionary
        return inventory