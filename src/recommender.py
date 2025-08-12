import pickle
import pandas as pd
from src.tmdb_utils import fetch_poster, fetch_movie_details

# Loading data at startup
movies = pickle.load(open('data/movie_list.pkl', 'rb'))
similarity = pickle.load(open('data/similarity.pkl', 'rb'))

def recommend(movie_title):
    """
    Finds and returns 5 similar movies with their details.
    """
    try:
        index = movies[movies['title'] == movie_title].index[0]
    except IndexError:
        return [] 

    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])

    recommended_movies = []
    for i in distances[1:6]:  
        movie_id = movies.iloc[i[0]].movie_id
        movie_title = movies.iloc[i[0]].title
        
        recommended_movies.append({
            'title': movie_title,
            'poster': fetch_poster(movie_id),
            'details': fetch_movie_details(movie_id)
        })
    return recommended_movies