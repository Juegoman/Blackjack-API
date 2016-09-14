"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from utils import create_deck
from utils import calc_val
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""
    deck = ndb.StringProperty(repeated=True, indexed=False)
    player_cards = ndb.StringProperty(repeated=True, indexed=False)
    dealer_cards = ndb.StringProperty(repeated=True, indexed=False)
    dealer_hidden = ndb.StringProperty(indexed=False)
    player_val = ndb.IntegerProperty(indexed=False)
    dealer_val = ndb.IntegerProperty(indexed=False)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')

    @classmethod
    def new_game(cls, user):
        """Creates and returns a new game"""
        game = Game(user=user,
                    game_over=False)
        game.deck = create_deck()

        for x in range(0, 2):
            game.player_cards.append(game.deck.pop())

        game.dealer_cards.append(game.deck.pop())
        game.dealer_hidden = game.deck.pop()

        game.player_val = calc_val(game.player_cards)
        game.dealer_val = calc_val(game.dealer_cards)

        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.player_cards = self.player_cards
        form.dealer_cards = self.dealer_cards
        form.player_val = self.player_val
        form.dealer_val = self.dealer_val
        form.game_over = self.game_over
        form.message = message
        return form

    def end_game(self, won=False, tied=False):
        """Ends the game - if won is True, the player won or tied. - if won is False,
        the player lost. If tied is True, then the player tied."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won, tied=tied)
        score.put()

    def reveal(self):
        if self.dealer_hidden:
            self.dealer_cards.append(self.dealer_hidden)
            self.dealer_hidden = ''
            self.dealer_val = calc_val(self.dealer_cards)
            self.put()

    def stand(self):
        """Handle the dealer's end game moves.
           Returns:
           0 if the dealer won
           1 if the dealer won by blackjack
           2 if a tie
           3 if the dealer busted
           4 if the player won by value."""
        dealerTurn = True
        self.reveal()

        if self.dealer_val == 21:
            # Dealer got a blackjack!
            return 1

        playerCurrVal = self.player_val
        while dealerTurn:
            dealerCurrVal = self.dealer_val

            if dealerCurrVal > playerCurrVal:
                # Dealer has a higher value than Player! Dealer wins!
                return 0
            elif dealerCurrVal == playerCurrVal:
                # Tie between Player and Dealer!
                return 2
            elif dealerCurrVal >= 17:
                # Player has higher value than Dealer! Player wins!
                return 4
            else:
                if not self.hit('D'):
                    # Dealer busts! Player wins!
                    return 3
        return 2

    def hit(self, tgt):
        """tgt should be 'D' for dealer or 'P' for player.
           Draw a card and recalculate value.
           If value is over 21 returns False, otherwise returns True."""
        card = self.deck.pop()

        result = None
        if tgt == 'D':
            self.dealer_cards.append(card)
            self.dealer_val = calc_val(self.dealer_cards)
            if self.dealer_val <= 21:
                result = True
            else:
                result = False

        elif tgt == 'P':
            self.player_cards.append(card)
            self.player_val = calc_val(self.player_cards)
            if self.player_val <= 21:
                result = True
            else:
                result = False

        else:
            return False
        self.put()
        return result


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    tied = ndb.BooleanProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), tied=self.tied)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    player_cards = messages.StringField(2, repeated=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)
    dealer_cards = messages.StringField(6, repeated=True)
    player_val = messages.IntegerField(7, required=True)
    dealer_val = messages.IntegerField(8, required=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    move = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    tied = messages.BooleanField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
