"""utils.py - File for collecting general utility functions."""

import logging
import random
from google.appengine.ext import ndb
import endpoints


def get_by_urlsafe(urlsafe, model):
    """Returns an ndb.Model entity that the urlsafe key points to. Checks
        that the type of entity returned is of the correct kind. Raises an
        error if the key String is malformed or the entity is of the incorrect
        kind
    Args:
        urlsafe: A urlsafe key string
        model: The expected entity kind
    Returns:
        The entity that the urlsafe Key string points to or None if no entity
        exists.
    Raises:
        ValueError:"""
    try:
        key = ndb.Key(urlsafe=urlsafe)
    except TypeError:
        raise endpoints.BadRequestException('Invalid Key')
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise endpoints.BadRequestException('Invalid Key')
        else:
            raise

    entity = key.get()
    if not entity:
        return None
    if not isinstance(entity, model):
        raise ValueError('Incorrect Kind')
    return entity


def create_deck():
    """Creates a deck and shuffles it."""
    cards = []
    card_suits = ['H', 'D', 'S', 'C']  # Heart, Diamond, Spade, Club
    card_ranks = ['2', '3', '4', '5', '6', '7', '8', '9',
                  '10', 'J', 'Q', 'K', 'A']
    for suit in card_suits:
        for rank in card_ranks:
            cards.append(suit + rank)

    random.shuffle(cards)
    return cards


def get_card_val(card, bigA=False):
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


def calc_val(cards):
    """Given an array of cards, find the value of the array.
       Will try to evaluate aces intelligently."""
    value = 0
    aces = []  # going to evaluate aces at the end.
    for card in cards:
        if card[1] == 'A':
            aces.append(card)
        else:
            value += get_card_val(card)
    for ace in aces:
        if value <= 10:
            value += get_card_val(ace, True)
        else:
            value += get_card_val(ace)
    return value
