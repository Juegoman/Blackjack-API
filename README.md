#Udacity Full Stack Nanodegree Project 7: Game API

A Google App Engine based API for creating and playing games of blackjack against an AI dealer.

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.



##Game Description:
Blackjack is a card game where the objective is to beat the dealer by getting a higher score than the dealer without exceeding 21. More information about the game can be read here: https://en.wikipedia.org/wiki/Blackjack
Many different blackjack games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Score Keeping:
Since Blackjack doesn't really have a "score", in the API a player's rank is determined by their win rate.
Wins are awarded 2 points and ties are awarded 1 point.
From there a user's win rate can be determined by dividing the user's points by two times the number of games the user has played (points / (2 * total_games)).

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - blackjack.py: A python implementation of blackjack which the API is based off of.
 - cron.yaml: Cronjob configuration.
 - index.yaml: Generated datastore index files.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper functions for retrieving ndb.Models by urlsafe Key string and various blackjack game functions.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Also adds a task to a task queue to update the average win rate
    for all games.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, move
    - Returns: GameForm with new game state.
    - Description: Accepts a 'move', either 'hit' or 'stand', and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).

 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_average_winrate**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average winrate of all games from a previously cached memcache key.

- **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: StringMessage
    - Description: Deletes the requested game and returns a message confirming the deletion.

- **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms
    - Description: Retrieves all of a user's games.
    Raises NotFoundException if a user cannot be found.

- **get_user_rankings**
    - Path: 'scores/ranking'
    - Method: GET
    - Parameters: None
    - Returns: StringMessages
    - Description: Returns an ordered and formatted list of users ranked by their winrate.

- **get_game_history**
    - Path: 'game/{urlsafe_game_key}/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: EventForms
    - Description: Returns a chronological list of moves made in a game.
    If a game cannot be found raises NotFoundException.

##Models Included:
 - **User**
    - Stores unique user_name, (optional) email address, and a user's ranking information (points and total_games).

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, player_cards, dealer_cards, player_val, dealer_val, game_over flag, message, user_name).
 - **NewGameForm**
    - Used to create a new game (user_name)
 - **MakeMoveForm**
    - Inbound make move form (move).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag, tied flag
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **GameForms**
    - Multiple GameForm container.
 - **StringMessage**
    - General purpose String container.
 - **StringMessages**
    - Multiple StringMessage container.
 - **EventForm**
    - Representation of a move in game history (event, description).
 - **EventForms**
    - Multiple EventForm container.
