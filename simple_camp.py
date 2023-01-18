import os
import json
import networkx
from networkx.algorithms.community import louvain_communities
import re

weight_threshold = 5
recommended_count = 10

def is_in_dict(w):
    '''
    TODO Judging if a word is in dictionary
    '''
    return True

def samurai_split(t, word_freq={}):
    '''
    TODO split tokens not in dictionary
    '''
    return t

def split(t):
    '''
    TODO custom splitter
    '''
    return re.split(r'\s\t\n', t)

def train(pull_requests):
    '''
    `pull_requests`: Pull requests from multiple projects
    Note that for each item `e` in `pull_request`, `e['text']` contains all textual content like commit messages,
    and paths of changed files; and `e['reviewers']` is a list of all reviewers' IDs.
    '''
    reviewer_set = set()
    for pr in pull_requests:
        reviewer_set |= set(pr['reviewers'])
        reviewer_set.add(pr['author'])
    
    reviewer_list = list(reviewer_set)
    g = networkx.Graph()
    for i in range(len(reviewer_list)):
        g.add_node(reviewer_list[i])
    
    for pr in pull_requests:
        reviewers = pr['reviewers']
        if 'author' in pr:
            reviewers.append(pr['author'])
        for i in range(len(reviewers)):
            for j in range(len(reviewers)):
                if i != j:
                    w = 0
                    if g.has_edge(reviewers[i], reviewers[j]):
                        w = g.get_edge_data(reviewers[i], reviewers[j])['weight']
                    
                    g.add_edge(reviewers[i], reviewers[j], weight=w + 1)
    
    partition = louvain_communities(g)
    reviewer_partition_map = {}
    for idx, p in enumerate(partition):
        for rev in p:
            reviewer_partition_map[rev] = idx
    
    all_known_words_freq = {}
    for pr in pull_requests:
        for t in split(pr['text']):
            if is_in_dict(t):
                all_known_words_freq[t] = all_known_words_freq.get(t, 0) + 1
    
    all_words = set()
    all_words_community_count = {}
    for pr in pull_requests:
        comms = set([reviewer_partition_map[r] for r in pr['reviewers']])
        for t in split(pr['text']):
            if not is_in_dict(t):
                split_result = set(samurai_split(t))
                for s in split_result:
                    if s not in all_words_community_count:
                        all_words_community_count[s] = set()
                    all_words_community_count[s] |= comms
                all_words |= split_result
            else:
                if t not in all_words_community_count:
                    all_words_community_count[t] = set()
                all_words_community_count[t] |= comms
                all_words.add(t)
            
    selected_words = [w for w in all_words if len(all_words_community_count[w]) <= len(partition) / 2]

    word_appearance_time = {}
    for r in reviewer_list:
        word_appearance_time[r] = {}
    for pr in pull_requests:
        for t in split(pr['text']):
            if not is_in_dict(t):
                split_result = set(samurai_split(t))
                for s in split_result:
                    if s not in selected_words:
                        continue
                    for r in pr['reviewers']:
                        word_appearance_time[r][s] = word_appearance_time[r].get(s, 0) + 1
            else:
                if t not in selected_words:
                    continue
                for r in pr['reviewers']:
                    word_appearance_time[r][t] = word_appearance_time[r].get(t, 0) + 1
    words_community_count = {c: len(s) for c, s in all_words_community_count.items() if c in selected_words}
    return (reviewer_list, g, partition, reviewer_partition_map, word_appearance_time, words_community_count)
    

def recommend(model, pr):
    '''
    model: trained model, 
    pr: incoming Pull request, containing `author` field.
    '''
    reviewer_list, graph, partition, reviewer_partition_map, word_appearance_time, words_community_count = model
    author = pr['author']
    p = reviewer_partition_map[author]
    candidate_set = partition[p]
    result = sorted([(k, v['weight']) for k, v in graph[author].items() if k in candidate_set], key=lambda x: x[1], reverse=True)
    result = [k for k, w in result if w > weight_threshold]
    if len(result) < recommended_count:
        d = {}
        score_map = {}
        for w in split(pr['text']):
            d[w] = d.get(w, 0) + 1
        for r in reviewer_list:
            e = word_appearance_time[r]
            common_words = d.keys() & e.keys()
            conf = sum([d[c] * e[c] / words_community_count[c] for c in common_words])
            score_map[r] = conf
        L = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        i = 0
        while i < len(L) and len(result) < recommended_count:
            if L[i][0] not in result:
                result.append(L[i][0])
            i += 1
    return result