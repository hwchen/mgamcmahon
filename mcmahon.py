#! /usr/bin/env python3

# Mcmahon pairing for MGA tournament

import random
import unittest

import yaml


class Player(object):

    def __init__(self, name, rank, aga_id, mm_score, mm_init, division):
        self.name = name
        self.rank = rank
        self.aga_id = aga_id
        self.mm_score = mm_score
        self.mm_init = mm_init
        self.division = division

    def __repr__(self):
        return ('<{:s}(name={:s}, rank={:d}, aga_id={:d}, mm_score={:d}, mm_init={:d}, division={:d})>'
                .format(self.__class__.__name__, self.name, self.rank, self.aga_id,
                        self.mm_score, self.mm_init, self.division))

    def __eq__(self, other):
        return type(other) is type(self) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return type(other) is not type(self) or self.__dict__ != other.__dict__


def player_representer(dumper, data):
    return dumper.represent_mapping('!player', data.__dict__)

yaml.add_representer(Player, player_representer)


def player_constructor(loader, node):
    player_dict = loader.construct_mapping(node)
    return Player(player_dict['name'], player_dict['rank'], player_dict['aga_id'],
                  player_dict['mm_score'], player_dict['mm_init'], player_dict['division'])

yaml.add_constructor('!player', player_constructor)


class Match(object):

    def __init__(self, white, black, winner=None):
        self.white = white
        self.black = black
        self.winner = winner

    def get_winner(self):
        return self._winner

    def set_winner(self, value):
        if value not in [self.white, self.black, None]:
            raise ValueError("'winner' must be equal to either 'white' or 'black' (or 'None')")
        self._winner = value

    winner = property(get_winner, set_winner)

    def __repr__(self):
        safe_winner = self.winner
        if safe_winner is None:
            safe_winner = "None"
        else:
            safe_winner = str(safe_winner)
        return ('<{:s}(white={:d}, black={:d}, winner={:s}>'
                .format(self.__class__.__name__, self.white, self.black, safe_winner))


class Tournament(object):

    def __init__(self, players, id_ctr, rounds, old_pairs, current_players):
        self.players = players
        self.id_ctr = id_ctr
        self.rounds = rounds
        self.old_pairs = old_pairs
        self.current_players = current_players

    @classmethod
    def new_tournament(cls, players=None):
        tournament = cls({}, 0, [], set(), set())
        if players is not None:
            for player in players:
                tournament.add_player(player)
        return tournament

    def calculate_mm_score(self):
        # set all mm_scores to original mm_score 
        for player in self.players.values():
            player.mm_score = player.mm_init 

        # iterate through each board in each round, add to mm_score when winner
        for idx, round_ in enumerate(self.rounds):
            if self.round_is_finished(idx):
                for board in round_.values():
                    self.players[board.winner].mm_score += 1

    def standings(self):
        return sorted(list(self.players.keys()), key=lambda k: self.players[k].mm_score,
                           reverse=True)

    def __eq__(self, other):
        return type(other) is type(self) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return type(other) is not type(self) or self.__dict__ != other.__dict__

    def add_player(self, player):
        self.players[self.id_ctr] = player
        self.id_ctr += 1

    def _pairing_is_valid(self, player_list):
        valid = True
        pairs = []
        temp_list = list(player_list)
        while temp_list:
            pairs.append(frozenset([temp_list.pop(), temp_list.pop()]))
        for pair in pairs:
            if pair in self.old_pairs:
                valid = False
                break
        return valid

    def pairing_score(self, player_list):
        # measures sum of difference of mm_score per pairing
        # assumes even number of people?
        score = 0
        temp_list = list(player_list)
        while temp_list:
            score += abs(self.players[temp_list.pop()].mm_score -
                         self.players[temp_list.pop()].mm_score)
        return score

    def _generate_ideal_candidate_pairings(self, sample_size):
        mm_scores = set()
        for player in self.players:
            mm_scores.add(player.mm_score)

        while i < sample_size:
            player_list = []
            for mm_score in mm_scores:
                player_sublist = [player_id for player_id, player in self.players.items()
                                  if player.mm_score == mm_score]
                random.shuffle(player_sublist)
                player_list.extend(player_sublist)
            yield player_list

#    def _generate_candidate_pairings(self, sample_size):
#        pairing = []
#        for i in range(sample_size):
#            player_list = []
#            temp_dict = {}
#            for player_key, player in self.players.items():
#                if player.division in temp_dict.keys():
#                    temp_dict[player.division].append(player_key)
#                else:
#                    temp_dict[player.division] = [player_key] 
#
#            for div in temp_dict.values():
#                random.shuffle(div)
#            
#            for div in temp_dict.values():
#                player_list.extend(div)
#
#            pairing.append(player_list)
#        return pairing

    def generate_pairing(self, sample_size):
        # populate old pairs set, skip if first round
        if self.rounds:
            for match in self.rounds[-1].values():
                self.old_pairs.add(frozenset([match.black, match.white]))
        
        # Generate candidate pairings for one division
        pairings = []  # list initialized for all pairings in a round
        div_dict = {}  # dict for paritioning player_keys into divisions
        # Create a dict of lists of divisions (list values are player_key)
        for player_key, player in self.players.items():
            if player.division in div_dict.keys():
                div_dict[player.division].append(player_key)
            else:
                div_dict[player.division] = [player_key] 

        # for each division, generate pairings and optimize.
        for div in div_dict.values():
            # generating possible pairings
            div_pairings = []  # list of lists of possible pairings
            for i in range(sample_size):
                random.shuffle(div)
                div_pairings.append(list(div))
            valid_pairings = [pairing for pairing in div_pairings
                              if self._pairing_is_valid(pairing)]
            # look for most optimized pairings
            best_score = 900000
            best_pairing = None
            for pairing in valid_pairings:
                pairing_score = self.pairing_score(pairing)
                if pairing_score < best_score:
                    best_score = pairing_score
                    best_pairing = pairing
            # append best pairing to pairings list
            pairings.append(best_pairing)
            print(best_score)
        return [player for division in pairings for player in division]
            
        #for div in div_dict.values():
        #    player_list.extend(div)
        #pairings.append(player_list)
        #print(best_score)

    def add_result(self, round_, board, winner):
        match = self.rounds[round_][board]
        match.winner = winner
        self.players[winner].mm_score += 1

    def round_is_finished(self, round_):
        finished = True
        for match in self.rounds[round_].values():
            if match.winner is None:
                finished = False
                break
        return finished

    def start_new_round(self, pairing):
        # check that last round is finished
        if len(self.rounds) > 0 and not self.round_is_finished(len(self.rounds) - 1):
            raise RuntimeError('Last round is not yet finished')

        # break pairing list into tuples
        pair_tuples = []
        while pairing:
            player_one = pairing.pop()
            player_two = pairing.pop()
            if (self.players[player_two].mm_score > self.players[player_one].mm_score):
                white = player_two
                black = player_one
            else:
                white = player_one
                black = player_two
            pair_tuples.append((white, black))

        # sort pairing and assign corresponding new Matches to boards
        sorted_pairing = sorted(pair_tuples, key=lambda p: self.players[p[0]].mm_score,
                                reverse=True)
        round_ = dict()
        for board in range(1, len(sorted_pairing) + 1):
            pair = sorted_pairing[board - 1]
            round_[board] = Match(pair[0], pair[1])
        self.rounds.append(round_)

    def wall_list(self):
        # results board sorts players by mmscore, and then shows each round's win
        # or loss per player
        # player, rank, round1, round2, .. roundn, mmscore.

        # build id_to_wall dict to hold conversion between tournament id and
        # wall list id (0 indexed, for now, convert to 1 index at end)
        current_standings = self.standings()
        id_to_wall = {player_id : current_standings.index(player_id)
                      for player_id in current_standings}

        # dictionary representation of the wall standings
        # key is tournament id, value is list of str representaiton (
        # opponent tournament id, win/loss)
        # no mm_score (will be pulled in at the end, along with player name)
        wall_dict = {player_id: list() for player_id in current_standings}

        # for each round, create record of each player's opponents and win/loss
        for idx, round_ in enumerate(self.rounds):
            if self.round_is_finished(idx):
                for match in round_.values():
                    winner_str = '+'
                    loser_str = '-'
                    if match.winner == match.black:
                        winner_str += str(id_to_wall[match.white] + 1)
                        loser_str += str(id_to_wall[match.black] + 1)
                        wall_dict[match.white].append(loser_str)
                    else:
                        winner_str += str(id_to_wall[match.black] + 1)
                        loser_str += str(id_to_wall[match.white] + 1)
                        wall_dict[match.black].append(loser_str)
                    wall_dict[match.winner].append(winner_str)
        res = []
        for standing, player_id in enumerate(current_standings):
            player_obj = self.players[player_id]
            # format opponents string
            opponents = ', '.join(wall_dict[player_id])
            res.append('{}. {} ({}) : {}'.format((standing +1), player_obj.name, player_obj.mm_score,
                                     opponents))
        return '\n'.join(res)

    def pairings_list(self):
        # pretty printing pairings list with board#, names.
        res = []
        current_round = self.rounds[-1]
        for board_key, board in current_round.items():
            res.append('{}: {} (W) v. {} (B)'.format(board_key, self.players[board.white].name,
                                                            self.players[board.black].name))
        return '\n'.join(res)

def tournament_representer(dumper, data):
    return dumper.represent_mapping('!tournament', data.__dict__)

yaml.add_representer(Tournament, tournament_representer)


def tournament_constructor(loader, node):
    tourn_dict = loader.construct_mapping(node)
    return Tournament(tourn_dict['players'], tourn_dict['id_ctr'], tourn_dict['rounds'],
                      tourn_dict['old_pairs'], tourn_dict['current_players'])

yaml.add_constructor('!tournament', tournament_constructor)


class PlayerTestCase(unittest.TestCase):

    def setUp(self):
        self.player_one = Player('Andrew', 10, 12345, 5, 5, 1)

    def test_repr(self):
        self.assertEqual(repr(self.player_one), '<Player(name=Andrew, rank=10,'
                                                ' aga_id=12345, mm_score=5, mm_init=5, division=1)>')

    def test_yaml(self):
        self.assertEqual(self.player_one, yaml.load(yaml.dump(self.player_one)))


class MatchTestCase(unittest.TestCase):

    def setUp(self):
        self.match = Match(1, 3)

    def test_repr(self):
        self.assertEqual(repr(self.match), '<Match(white=1, black=3, winner=None>')

    def test_winner(self):
        with self.assertRaises(ValueError):
            self.match.winner = 4
        self.match.winner = 3
        self.assertEqual(repr(self.match), '<Match(white=1, black=3, winner=3>')


class TournamentTestCase(unittest.TestCase):

    def setUp(self):
        players = [Player('Ma Wang', 7, 12345, 6, 6, 1),
                   Player('Will', 4, 1235, 6, 6, 1),
                   Player('Steve', 4, 234, 6, 6, 1),
                   Player('Mr. Cho', 3, 54, 6, 6, 1),
                   Player('XiaoCheng', 3, 5723, 6, 6, 1),
                   Player('Alex', 1, 632, 6, 6, 1),
                   Player('Matt', 4, 5723, 6, 6, 1),
                   Player('Ed', 2, 5723, 6, 6, 1),
                   Player('Josh', 1, 5723, 6, 6, 1),
                   Player('Kevin', 1, 5723, 6, 6, 1),
                   Player('Gus', 1, 5723, 1, 1, 2),
                   Player('Pete', -2, 5723, 1, 1, 2),
                   Player('Dan', -1, 5723, 1, 1, 2),
                   Player('David', -2, 5723, 1, 1, 2),
                   Player('Alex', -3, 5723, 1, 1, 2),
                   Player('Eric', -4, 5723, 1, 1, 2),
                   Player('Makio', -4, 5723, 1, 1, 2),
                   Player('David', -4, 5723, 1, 1, 2),
                   Player('Eric', -4, 5723, 1, 1, 2),
                   Player('Howie', -4, 5723, 1, 1, 2),
                   ]
        self.tournament = Tournament.new_tournament(players)
        self.pairing = self.tournament.generate_pairing(10000)

    def test_yaml(self):
        self.assertEqual(self.tournament, yaml.load(yaml.dump(self.tournament)))

    def test_generate_pairing(self):
        self.assertEqual(self.tournament.pairing_score(self.pairing), 0)

    def test_new_round(self):
        self.tournament.start_new_round(self.pairing)
        # check that a round was generated and added to the list
        self.assertEqual(len(self.tournament.rounds), 1)
        # check that the round isn't finished
        self.assertFalse(self.tournament.round_is_finished(0))
        with self.assertRaises(RuntimeError):
            self.tournament.start_new_round(self.pairing)

    def test_results(self):
        self.tournament.start_new_round(self.pairing)
        round_ = self.tournament.rounds[0]
        for board in round_.keys():
            # choose a random winner
            match = round_[board]
            self.tournament.add_result(0, board, (match.white if random.randint(0, 1)
                                                  else match.black))
        self.assertTrue(self.tournament.round_is_finished(0))

if __name__ == '__main__':
    unittest.main()
