# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_WINRATE = 'WINRATE'


@endpoints.api(name='blackjack', version='v1')
class BlackjackApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        game = Game.new_game(user.key)
        message = 'Good luck playing blackjack! Your hand is'
        for card in game.player_cards:
            message += ' ' + card
        message += '. Dealer hand is ' + game.dealer_cards[0] + '.'

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_winrate')
        return game.to_form(message)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move! HIT or STAND?')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')

        if game.player_val == 21 and len(game.player_cards) == 2:
            # player has a blackjack, checking if the dealer has a blackjack.
            game.reveal()
            if game.dealer_val == 21 and len(game.dealer_cards) == 2:
                game.end_game(True, True)
                return game.to_form("You tied with the Dealer!")
            else:
                game.end_game(True)
                return game.to_form("You win with a blackjack!")
        if request.move.lower() == 'hit':
            if game.hit('P'):
                message = 'Your hand is'
                for card in game.player_cards:
                    message += ' ' + card
                return game.to_form(message)
            else:
                game.end_game()
                message = 'You busted with a value of ' + str(game.player_val)
                return game.to_form(message)
        elif request.move.lower() == 'stand':
            result = game.stand()
            # result key:
            # 0 if the dealer won
            # 1 if the dealer won by blackjack
            # 2 if a tie
            # 3 if the dealer busted
            # 4 if the player won by value.
            if result == 0:
                game.end_game()
                return game.to_form("The dealer has a higher value than you! "
                                    "You lose!")
            elif result == 1:
                game.end_game()
                return game.to_form("The dealer got a blackjack! You lose!")
            elif result == 2:
                game.end_game(True, True)
                return game.to_form("You tied with the Dealer!")
            elif result == 3:
                game.end_game(True)
                return game.to_form("The Dealer busted! You win!")
            elif result == 4:
                game.end_game(True)
                return game.to_form("You have a higher value than the dealer! "
                                    "You win!")
            else:
                game.to_form("Unknown error: " + str(result))
        else:
            return game.to_form('Please enter either HIT or STAND.')

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_winrate',
                      name='get_average_winrate',
                      http_method='GET')
    def get_average_winrate(self, request):
        """Get the cached average winrate"""
        return StringMessage(message=memcache.get(MEMCACHE_WINRATE) or '')

    @staticmethod
    def _cache_average_winrate():
        """Populates memcache with the average winrate of Games"""
        scores = Score.query().fetch()
        if scores:
            count = len(scores)
            total_wins = 0
            for score in scores:
                if score.won:
                    total_wins += 1

            average = float(total_wins)/count
            memcache.set(MEMCACHE_WINRATE,
                         'The average winrate is {:.2f}'
                         .format(average))


api = endpoints.api_server([BlackjackApi])
