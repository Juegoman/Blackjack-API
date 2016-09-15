"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

from utils import create_deck, calc_val
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    points = ndb.IntegerProperty(default=0)
    total_games = ndb.IntegerProperty(default=0)


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
    history = ndb.StringProperty(repeated=True, indexed=False)

    EVENTS = {
        'START': "Game Started with player cards {} and {}. The dealer's shown"
                 " card is {} and their hidden card is {}.",
        'GAME_OVER': 'Game ended',
        'REVEAL': 'Dealer revealed their hidden card {}.',
        'STAND': 'Player stands and dealer begins their move.',
        'P_HIT': 'Player hits and draws {}',
        'D_HIT': 'Dealer hits and draws {}',
        'P_BUST': 'Player cards over 21 and they busted. They lose.',
        'D_BUST': 'Dealer cards over 21 and they busted. They lose.',
        'P_BLK_JK': 'Player has a blackjack! They win!',
        'D_BLK_JK': 'Dealer has a blackjack! They win!',
        'P_WIN': 'Player has a higher value than the Dealer and wins.',
        'D_WIN': 'Dealer has a higher value than the Player and wins.',
        'TIE': 'Player and dealer have the same value so they tie.'
    }

    @classmethod
    def new_game(cls, user):
        """Creates and returns a new game"""
        game = Game(user=user,
                    game_over=False)
        game.deck = create_deck()
        start_string = 'START'

        for x in range(2):
            card = game.deck.pop()
            start_string += '.' + card
            game.player_cards.append(card)

        card = game.deck.pop()
        start_string += '.' + card
        game.dealer_cards.append(card)
        card = game.deck.pop()
        start_string += '.' + card
        game.dealer_hidden = card

        game.player_val = calc_val(game.player_cards)
        game.dealer_val = calc_val(game.dealer_cards)

        game.history.append(start_string)

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

    def get_history(self):
        """Returns a formatted game history."""
        history = EventForms()
        for event in self.history:
            form = EventForm()
            # certain events have relevant cards attached to them,
            # the following procedure separates them.
            split_event = event.split('.')
            event_name = split_event[0]
            form.event = event_name
            if event_name == "START":
                form.description = Game.EVENTS[event_name].format(
                    split_event[1],
                    split_event[2],
                    split_event[3],
                    split_event[4]
                )
            elif event_name == "REVEAL" or 'HIT' in event_name:
                form.description = Game.EVENTS[event_name].format(
                    split_event[1]
                )
            else:
                form.description = Game.EVENTS[event_name]
            history.events.append(form)
        return history

    def append_history(self, event):
        """Appends an event to the game history."""
        self.history.append(event)
        self.put()

    def end_game(self, won=False, tied=False):
        """Ends the game - if won is True, the player won or tied.
           If won is False, the player lost.
           If tied is True, then the player tied."""
        self.history.append('GAME_OVER')
        self.game_over = True
        self.put()

        # Recalculate the user's points
        user = User.query(User.key == self.user).get()
        if tied:
            user.points += 1
        elif won:
            user.points += 2
        user.total_games += 1
        user.put()

        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won, tied=tied)
        score.put()

    def reveal(self):
        if self.dealer_hidden:
            self.dealer_cards.append(self.dealer_hidden)
            reveal_string = 'REVEAL.' + self.dealer_hidden
            self.dealer_hidden = ''
            self.dealer_val = calc_val(self.dealer_cards)
            self.history.append(reveal_string)
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
        self.history.append('STAND')
        self.reveal()
        result = 2

        if self.dealer_val == 21:
            # Dealer got a blackjack!
            result = 1
            dealerTurn = False
            self.history.append('D_BLK_JK')

        playerCurrVal = self.player_val
        while dealerTurn:
            dealerCurrVal = self.dealer_val

            if dealerCurrVal > playerCurrVal:
                # Dealer has a higher value than Player! Dealer wins!
                result = 0
                dealerTurn = False
                self.history.append('D_WIN')
            elif dealerCurrVal == playerCurrVal:
                # Tie between Player and Dealer!
                result = 2
                dealerTurn = False
                self.history.append('TIE')
            elif dealerCurrVal >= 17:
                # Player has higher value than Dealer! Player wins!
                result = 4
                dealerTurn = False
                self.history.append('P_WIN')
            else:
                if not self.hit('D'):
                    # Dealer busts! Player wins!
                    result = 3
                    dealerTurn = False
                    self.history.append('D_BUST')
        self.put()
        return result

    def hit(self, tgt):
        """tgt should be 'D' for dealer or 'P' for player.
           Draw a card and recalculate value.
           If value is over 21 returns False, otherwise returns True."""
        card = self.deck.pop()
        event_string = '.' + card
        if tgt == 'D':
            self.dealer_cards.append(card)
            self.dealer_val = calc_val(self.dealer_cards)
            self.history.append('D_HIT' + event_string)
            if self.dealer_val <= 21:
                result = True
            else:
                result = False

        elif tgt == 'P':
            self.player_cards.append(card)
            self.player_val = calc_val(self.player_cards)
            self.history.append('P_HIT' + event_string)
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


class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class StringMessages(messages.Message):
    """StringMessages -- outbound string messages"""
    messages = messages.StringField(1, repeated=True)


class EventForm(messages.Message):
    """EventForm for game history"""
    event = messages.StringField(1, required=True)
    description = messages.StringField(2, required=True)


class EventForms(messages.Message):
    """Return Game history events"""
    events = messages.MessageField(EventForm, 1, repeated=True)

