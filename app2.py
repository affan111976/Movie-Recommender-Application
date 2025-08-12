import streamlit as st
import pandas as pd
import logging
from src.tmdb_utils import fetch_poster
from src.recommender import recommend, movies
from src.Database.database import init_database, get_db_session
from src.Database.user_manager import UserManager
from src.Database.models import WatchlistItem, Rating, User, Feedback
from src.admin.admin_pages import admin_dashboard_page

# Setting up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Movie Recommender System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initializing UserManager
user_manager = UserManager()

def login_page():
    st.markdown('<h1 class="main-header">🎬 Movie Recommender - Login</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username and password:
                    try:
                        user_data = user_manager.authenticate_user(username, password)
                        if user_data:
                            st.session_state.user_id = user_data['id']
                            st.session_state.username = user_data['username']
                            st.session_state.is_admin = user_data['is_admin'] 
                            st.session_state.logged_in = True
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")
                        logger.error(f"Login error for user {username}: {e}")
                else:
                    st.error("Please fill in all fields")
    with tab2:
        st.subheader("Create New Account")
        with st.form("register_form"):
            reg_username = st.text_input("Username", key="reg_username")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            terms_consent = st.checkbox("I agree to the terms of service and privacy policy")
            reg_submitted = st.form_submit_button("Register")
            if reg_submitted:
                if reg_username and reg_email and reg_password and terms_consent:
                    try:
                        user_data = user_manager.create_user(username=reg_username, email=reg_email, password=reg_password)
                        if user_data:
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error("Failed to create account. Username or email might already exist.")
                    except Exception as e:
                        st.error(f"Registration error: {str(e)}")
                        logger.error(f"Registration error: {e}")
                else:
                    st.error("Please fill in all required fields and accept terms")

def recommender_page():
    st.title('🎬 Movie Recommender System')
    if 'selected_movie' not in st.session_state:
        st.session_state.selected_movie = None
    st.sidebar.header("Explore & Discover")
    all_genres = ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Drama', 'Fantasy', 'Horror', 'ScienceFiction', 'Thriller']
    display_genres = ["-"] + [g.replace('ScienceFiction', 'Science Fiction') for g in all_genres]
    selected_display_genre = st.sidebar.selectbox("Browse by Genre", display_genres)
    if selected_display_genre != "-":
        selected_genre = selected_display_genre.replace('Science Fiction', 'ScienceFiction')
        st.header(f"Top Movies in {selected_display_genre}")
        genre_movies = movies[movies['genres'].apply(lambda x: selected_genre in x)].head(10)
        if not genre_movies.empty:
            cols = st.columns(5)
            for i, (idx, row) in enumerate(genre_movies.iterrows()):
                with cols[i % 5]:
                    movie_id = row['movie_id']
                    poster_url = fetch_poster(movie_id)
                    st.image(poster_url, use_container_width=True)
                    st.caption(row['title'])
        else:
            st.write("No movies found for this genre in the current dataset.")
    st.sidebar.markdown("---")
    st.sidebar.header("Get Recommendations")
    movie_list = movies['title'].values
    selected_title = st.sidebar.selectbox("Type or select a movie", options=movie_list, key='movie_selector')
    if st.sidebar.button('Get Recommendations'):
        st.session_state.selected_movie = selected_title
    if st.session_state.selected_movie:
        st.header(f"Recommendations for: *{st.session_state.selected_movie}*")
        recommended_movies = recommend(st.session_state.selected_movie)
        if recommended_movies:
            cols = st.columns(5)
            for i, movie in enumerate(recommended_movies):
                movie_id = movies[movies['title'] == movie['title']].iloc[0]['movie_id']
                with cols[i % 5]:
                    st.image(movie['poster'], use_container_width=True)
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("➕", key=f"watch_{movie_id}", help="Add to Watchlist"):
                            try:
                                with get_db_session() as session:
                                    exists = session.query(WatchlistItem).filter_by(user_id=st.session_state.user_id, movie_id=movie_id).first()
                                    if not exists:
                                        new_item = WatchlistItem(user_id=st.session_state.user_id, movie_id=movie_id, movie_title=movie['title'])
                                        session.add(new_item)
                                        st.toast(f"Added '{movie['title']}' to your watchlist!")
                                    else:
                                        st.toast(f"'{movie['title']}' is already in your watchlist.")
                            except Exception as e:
                                logger.error(f"Error adding to watchlist: {e}")
                                st.error("Could not add to watchlist.")
                    if st.button(movie['title'], key=f"title_{movie_id}"):
                        st.session_state.selected_movie = movie['title']
                        st.rerun()
                    with st.expander(" More Info"):
                        st.write(f"**Release Date:** {movie['details']['release_date']}")
                        st.write(f"**Rating:** {movie['details']['vote_average']:.1f}/10")
                        st.markdown(f"**Overview:** {movie['details']['overview']}")
                        if movie['details']['trailer_key']:
                            st.video(f"https://www.youtube.com/watch?v={movie['details']['trailer_key']}")
                        else:
                            st.text("No trailer available.")
        else:
            st.error("Could not find recommendations for this movie.")
    else:
        st.info("Select a movie from the sidebar and click 'Get Recommendations' to start.")

def user_dashboard():
    st.title(f"Dashboard for {st.session_state.username}")
    tab1, tab2, tab3 = st.tabs(["My Watchlist", "My Ratings", "👤 Profile & Settings"])
    with tab1:
        st.header("🎬 Movies to Watch")
        try:
            with get_db_session() as session:
                watchlist_items = session.query(WatchlistItem).filter_by(user_id=st.session_state.user_id).order_by(WatchlistItem.added_at.desc()).all()
                if not watchlist_items:
                    st.info("Your watchlist is empty.")
                else:
                    cols = st.columns(4)
                    for i, item in enumerate(watchlist_items):
                        with cols[i % 4]:
                            st.image(fetch_poster(item.movie_id), use_container_width=True)
                            st.caption(item.movie_title)
                            if st.button("🗑️ Remove", key=f"remove_watchlist_{item.id}", help="Remove from watchlist"):
                                item_to_delete = session.query(WatchlistItem).get(item.id)
                                if item_to_delete:
                                    session.delete(item_to_delete)
                                    session.commit()
                                    st.toast(f"Removed '{item.movie_title}' from watchlist!")
                                    st.rerun()
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            st.error("Could not load your watchlist.")
    with tab2:
        st.header("⭐ My Movie Ratings")
        try:
            with get_db_session() as session:
                user_ratings = session.query(Rating).filter_by(user_id=st.session_state.user_id).order_by(Rating.created_at.desc()).all()
                if not user_ratings:
                    st.info("You haven't rated any movies yet.")
                else:
                    for rating in user_ratings:
                        movie_info = movies.loc[movies['movie_id'] == rating.movie_id]
                        if not movie_info.empty:
                            movie_title = movie_info['title'].iloc[0]
                            with st.container():
                                col1, col2 = st.columns([1, 3])
                                with col1:
                                    st.image(fetch_poster(rating.movie_id))
                                with col2:
                                    st.subheader(movie_title)
                                    new_rating_val = st.slider("Update your rating", 1, 10, int(rating.rating), key=f"dash_slider_{rating.id}")
                                    btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                                    with btn_col1:
                                        if st.button("Update", key=f"update_rating_{rating.id}"):
                                            rating_to_update = session.query(Rating).get(rating.id)
                                            rating_to_update.rating = float(new_rating_val)
                                            session.commit()
                                            st.toast(f"Updated rating for '{movie_title}'!")
                                            st.rerun()
                                    with btn_col2:
                                        if st.button("Delete", key=f"delete_rating_{rating.id}"):
                                            rating_to_delete = session.query(Rating).get(rating.id)
                                            session.delete(rating_to_delete)
                                            session.commit()
                                            st.toast(f"Deleted your rating for '{movie_title}'!")
                                            st.rerun()
                                st.markdown("---")
        except Exception as e:
            logger.error(f"Error loading ratings: {e}")
            st.error("Could not load your ratings.")
    with tab3:
        st.header("Profile Information")
        try:
            with get_db_session() as session:
                user = session.query(User).get(st.session_state.user_id)
                if user:
                    st.text_input("Username", value=user.username, disabled=True)
                    st.text_input("Email", value=user.email, disabled=True)
                    st.text_input("Member Since", value=user.created_at.strftime("%B %d, %Y"), disabled=True)
                with st.expander("Edit Profile"):
                    with st.form("profile_form"):
                        st.write("Leave a field blank to keep the current value.")
                        new_username = st.text_input("New Username", placeholder="Enter new username")
                        new_email = st.text_input("New Email", placeholder="Enter new email address")
                        submitted = st.form_submit_button("Save Changes")
                        if submitted:
                            if not new_username and not new_email:
                                st.warning("Please enter a new username or email to update.")
                            else:
                                success, message = user_manager.update_user_profile(user_id=st.session_state.user_id, new_username=new_username or None, new_email=new_email or None)
                                if success:
                                    st.success(message)
                                    if new_username:
                                        st.session_state.username = new_username
                                    st.rerun()
                                else:
                                    st.error(message)
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            st.error("Could not load your profile.")

def feedback_page():
    st.title("📝 Submit Feedback")
    st.write("We value your feedback! Please let us know what you think.")
    with st.form("feedback_form"):
        feedback_text = st.text_area("Your feedback", height=150, placeholder="Tell us about your experience, suggest a feature, or report a bug.")
        submitted = st.form_submit_button("Submit Feedback")
        if submitted:
            if not feedback_text.strip():
                st.warning("Please enter some feedback before submitting.")
            else:
                success = user_manager.submit_feedback(user_id=st.session_state.user_id, feedback_text=feedback_text)
                if success:
                    st.success("Thank you for your feedback! We appreciate you helping us improve.")
                else:
                    st.error("Sorry, we couldn't submit your feedback at this time. Please try again later.")

def search_and_rate_page():
    st.title("🔎 Search and Rate Movies")
    search_query = st.text_input("Enter a movie title to search", "")
    if search_query:
        results = movies[movies['title'].str.contains(search_query, case=False, na=False)]
        if not results.empty:
            st.subheader(f"Found {len(results)} results for '{search_query}'")
            for index, row in results.iterrows():
                movie_id = row['movie_id']
                movie_title = row['title']
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(fetch_poster(movie_id), use_container_width=True)
                with col2:
                    st.subheader(movie_title)
                    rating_val = st.slider("Your Rating (1-10)", 1, 10, 5, key=f"search_rate_slider_{movie_id}")
                    if st.button("⭐ Rate", key=f"search_rate_btn_{movie_id}"):
                        try:
                            with get_db_session() as session:
                                existing_rating = session.query(Rating).filter_by(user_id=st.session_state.user_id, movie_id=movie_id).first()
                                if existing_rating:
                                    existing_rating.rating = float(rating_val)
                                    st.toast(f"Updated your rating for '{movie_title}' to {rating_val}!")
                                else:
                                    new_rating = Rating(user_id=st.session_state.user_id, movie_id=movie_id, rating=float(rating_val))
                                    session.add(new_rating)
                                    st.toast(f"You rated '{movie_title}' {rating_val}/10!")
                        except Exception as e:
                            logger.error(f"Error submitting rating from search: {e}")
                            st.error("Could not submit rating.")
                st.markdown("---")
        else:
            st.warning(f"No movies found matching '{search_query}'. Please try another title.")
    else:
        st.info("Type a movie title above to begin your search.")

def main():
    if not init_database():
        st.error("Failed to initialize database. Please check your configuration.")
        return
        
    user_manager.ensure_admin_exists()

    if 'logged_in' not in st.session_state or not st.session_state.get('logged_in', False):
        login_page()
        return

    st.sidebar.success(f"Logged in as {st.session_state.username}")
    
    # Navigation options
    nav_options = ["Movie Recommender", "Search & Rate", "My Dashboard", "Submit Feedback"]
    
    if st.session_state.get('is_admin', False):
        nav_options.append("Admin Dashboard")

    page = st.sidebar.radio("Navigation", nav_options)
    
    if st.sidebar.button("Logout"):
        for key in ['logged_in', 'user_id', 'username', 'is_admin']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # Page Routing 
    if page == "Movie Recommender":
        recommender_page()
    elif page == "Search & Rate":
        search_and_rate_page()
    elif page == "My Dashboard":
        user_dashboard()
    elif page == "Submit Feedback":
        feedback_page()
    elif page == "Admin Dashboard":
        admin_dashboard_page()

if __name__ == '__main__':
    main()
