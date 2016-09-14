import random


class BlackjackGame:
    def __init__(self):
        self.deck = Deck()
        self.player = Player(self.deck)
        self.dealer = Dealer(self.deck)

    def start(self):
        self.player.start()
        self.dealer.start()

    def getPlayer(self):
        return self.player

    def getDealer(self):
        return self.dealer

    def reveal(self):
        """Reveal the dealer's hand"""
        self.dealer.reveal()

    def hit(self, tgt):
        """tgt should be 'D' for dealer or 'P' for player."""
        if tgt == 'D':
            return self.dealer.hit()
        elif tgt == 'P':
            return self.player.hit()
        else:
            print "Invalid tgt parameter!: " + tgt


class Dealer:
    """A representation of a dealer"""
    def __init__(self, deck):
        """Create a reference to the deck and instatiate variables"""
        self.deck = deck
        self.shown_cards = []
        self.hidden_card = ''
        self.value = 0

    def start(self):
        for card in self.deck.draw(1):
            self.shown_cards.append(card)
        self.value = calcVal(self.shown_cards)
        for card in self.deck.draw(1):
            self.hidden_card = card

    def reveal(self):
        self.shown_cards.append(self.hidden_card)
        self.hidden_card = ''
        self.value = calcVal(self.shown_cards)

    def hit(self):
        """Draw a card and recalculate value.
           If value is over 21 returns False, otherwise returns True."""
        card = self.deck.draw(1)[0]
        self.shown_cards.append(card)
        self.value = calcVal(self.shown_cards)
        result = None
        if self.value <= 21:
            result = True
        else:
            result = False
        return result

    def getCards(self):
        return self.shown_cards

    def getVal(self):
        return self.value


class Player:
    """A representation of a player"""
    def __init__(self, deck):
        """Create a reference to the deck and instatiate variables"""
        self.deck = deck
        self.cards = []
        self.value = 0

    def start(self):
        for card in self.deck.draw(2):
            self.cards.append(card)
        self.value = calcVal(self.cards)

    def hit(self):
        """Draw a card and recalculate value.
           If value is over 21 returns False, otherwise returns True."""
        card = self.deck.draw(1)[0]
        self.cards.append(card)
        self.value = calcVal(self.cards)
        result = None
        if self.value <= 21:
            result = True
        else:
            result = False
        return result

    def getCards(self):
        return self.cards

    def getVal(self):
        return self.value


class Deck:
    """A representation of a 52 card deck."""
    def __init__(self):
        """Creates a deck and shuffles it."""
        self.cards = []
        self.discards = []
        card_suits = ['H', 'D', 'S', 'C']  # Heart, Diamond, Spade, Club
        card_ranks = ['2', '3', '4', '5', '6', '7', '8', '9',
                      '10', 'J', 'Q', 'K', 'A']
        for suit in card_suits:
            for rank in card_ranks:
                self.cards.append(suit + rank)

        random.shuffle(self.cards)

    def draw(self, num):
        """Removes num cards from the deck to the
           drawn history and returns them."""
        result = []
        for x in range(0, num):
            drawn = self.cards.pop()
            self.discards.append(drawn)
            result.append(drawn)
        return result

    def reset(self):
        """Resets the deck and shuffles it."""
        for discard in self.discards:
            self.cards.append(discard)
        self.discards = []
        random.shuffle(self.cards)


def BlackjackHandler(game):
    print "Starting game!"
    game.start()

    outputStr = "Player drew "
    for card in game.getPlayer().getCards():
        outputStr += card + ' '
    print outputStr
    outputStr = "Player value is " + str(game.getPlayer().getVal())
    print outputStr

    outputStr = ("Dealer drew " + game.getDealer().getCards()[0] +
                 " and has a hidden card.")
    print outputStr
    outputStr = "Dealer's current value is " + str(game.getDealer().getVal())
    print outputStr

    if game.getPlayer().getVal() == 21:
        print "Player has a blackjack! Checking if Dealer has a blackjack..."
        game.reveal()
        if game.getDealer().getVal() < 21:
            print "Player wins with a blackjack!"
        else:
            print "Tie between Player and Dealer!"
        return 0

    playerTurn = True
    while playerTurn:
        playerAction = raw_input("You may either HIT or STAND: ")
        if playerAction == 'HIT':
            print "Hit me!"
            if game.hit('P'):
                outputStr = "Your cards are "
                for card in game.getPlayer().getCards():
                    outputStr += card + ' '
                print outputStr
                outputStr = "Player value is " + str(game.getPlayer().getVal())
                print outputStr
            else:
                outputStr = "Your cards are "
                for card in game.getPlayer().getCards():
                    outputStr += card + ' '
                print outputStr
                outputStr = "Player value is " + str(game.getPlayer().getVal())
                print outputStr
                print "Sorry but you busted! Player loses."
                return 0
        elif playerAction == 'STAND':
            print "Player stands."
            playerTurn = False
        else:
            print "Please input either HIT or STAND."

    dealerTurn = True
    game.reveal()

    if game.getDealer().getVal() == 21:
        print "Dealer has a blackjack! Dealer wins!"
        return 0

    playerCurrVal = game.getPlayer().getVal()
    while dealerTurn:
        dealerCurrVal = game.getDealer().getVal()
        outputStr = "Dealer's cards are "
        for card in game.getDealer().getCards():
            outputStr += card + ' '
        print outputStr
        outputStr = "Dealer value is " + str(dealerCurrVal)
        print outputStr

        if dealerCurrVal > playerCurrVal:
            print "Dealer has a higher value than Player! Dealer wins!"
            dealerTurn = False
        elif dealerCurrVal == playerCurrVal:
            print "Tie between Player and Dealer!"
            dealerTurn = False
        elif dealerCurrVal >= 17:
            print "Player has higher value than Dealer! Player wins!"
            dealerTurn = False
        else:
            if game.hit('D'):
                print "Dealer hits."
            else:
                print "Dealer busts! Player wins!"
                dealerTurn = False
    return 0


def getCardVal(card, bigA=False):
    """Given a card, find its value. if bigA is True, evaluate aces as 11."""
    if len(card) == 3:
        rank = card[1] + card[2]
    else:
        rank = card[1]
    if rank in 'A':
        if bigA:
            return 11
        else:
            return 1
    elif rank in 'JQK':
        return 10
    else:
        return int(rank)


def calcVal(cards):
    """Given an array of cards, find the value of the array.
       Will try to evaluate aces intelligently."""
    value = 0
    aces = []  # going to evaluate aces at the end.
    for card in cards:
        if card[1] == 'A':
            aces.append(card)
        else:
            value += getCardVal(card)
    for ace in aces:
        if value <= 10:
            value += getCardVal(ace, True)
        else:
            value += getCardVal(ace)
    return value

# game = BlackjackGame()
# BlackjackHandler(game)
