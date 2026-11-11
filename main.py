from random import randint
from drafter import *
from dataclasses import dataclass

def sort_hand(hand):
    if hand[0]<hand[1]:
        hand[0],hand[1] = hand[1],hand[0]
    if hand[1]<hand[2]:
        hand[1],hand[2] = hand[2],hand[1]
    if hand[0]<hand[1]:
        hand[0],hand[1] = hand[1],hand[0]
    return hand

def hand_to_string(hand):
    rep="0A23456789XJQKA"
    return rep[hand[0]]+rep[hand[1]]+rep[hand[2]]

def has_pair(hand):
    if hand[0]==hand[1] or hand[1]==hand[2]:
        return True
    return False

def has_straight(hand):
    return hand[0]==hand[1]+1==hand[2]+2

def has_triple(hand):
    return hand[0]==hand[1]==hand[2]

def score_hand(hand):
    bonus=16**3
    score=hand[0]*16**2 + hand[1]*16 + hand[2]
    if has_triple(hand):
        score += bonus*16
    elif has_straight(hand):
        score += bonus*15
    elif has_pair(hand):
        score += bonus*hand[1]
    return score

def dealer_plays(hand):
    return score_hand(hand) >= score_hand([12,3,2])

def deal():
    """Simple random card dealing function"""
    return [randint(2, 14), randint(2, 14), randint(2, 14)]

"""
__deck__ = []
def deal():
    if not __deck__:
        raise RuntimeError("Deal at most two hands per round!")
    return __deck__.pop(0)

def fix_deal(cards):
    global __deck__
    __deck__ = cards
    return play_round()
"""


@dataclass
class State:
    hand: list[int]
    dealer_hand: list[int]
    score: int


def decide_game(state: State) -> str:
    if not dealer_plays(state.dealer_hand):
        state.score += 10
        dealer_action = "folded"
    elif score_hand(sort_hand(state.dealer_hand)) < score_hand(sort_hand(state.hand)):
        state.score += 20
        dealer_action = "lost"
    else:
        state.score += -20
        dealer_action = "won"
    return dealer_action


@route
def index(state: State):
    state.hand = deal()
    state.dealer_hand = deal()
    return Page(
        state,
        [
            Header("New round!"),
            "Your score: " + str(state.score),
            "Your hand: " + hand_to_string(state.hand),
            Button("Fold", fold),
            Button("Play", play),
        ],
    )


@route
def fold(state: State):
    state.score -= 10
    return Page(
        state,
        [
            Header("You folded!"),
            "You lost 10 points. Your score is now " + str(state.score),
            Button("Start new game", index),
        ],
    )


@route
def play(state: State):
    dealer_action = decide_game(state)
    return Page(
        state,
        [
            Header("Dealer " + dealer_action + "!"),
            "Your hand: " + hand_to_string(state.hand),
            "The dealer's hand: " + hand_to_string(state.dealer_hand),
            "The dealer " + dealer_action + " and your score is now " + str(state.score) + " points.",
            Button("Start new game", index),
        ],
    )


start_server(State([], [], 0))
