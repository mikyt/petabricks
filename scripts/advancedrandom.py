import random

def random_roulette_selection(weighted_candidates):
    """Perform roulette selection between the given candidates.
weighted_candidates is a list of pairs (weight, candidate).

The higher the weight, the higher the probability of being chosen"""
    total_weight = sum(candidate[0] for candidate in weighted_candidates)
    
    winner = random.uniform(0,1) * total_weight
    
    weight_sum = 0
    for candidate in weighted_candidates:
        weight = candidate[0]
        new_weight_sum = weight_sum + weight
        if weight_sum <= winner and winner < new_weight_sum:
            winner_content = candidate[1]
            return winner_content
        weight_sum = new_weight_sum
    
    #If we are here, winner=1
    #We have to return the last candidate
    num_candidates = len(weighted_candidates)
    last_candidate = weighted_candidates[num_candidates-1] 
    return last_candidate[1]