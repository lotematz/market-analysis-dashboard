import requests
import json
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
import seaborn as sns
import matplotlib.pyplot as plt

# הגדרות תצוגה
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY").strip()

st.set_page_config(page_title="SWOT Market Analysis", layout="wide")

# ------------------------ ממשק משתמש + הגדרות לשליפת נתונים -----------------------------
st.sidebar.header("הגדרות חיפוש")

locations = {
    "תל אביב": {"lat": 32.0853, "lng": 34.7818},
    "ירושלים": {"lat": 31.7683, "lng": 35.2137},
    "חיפה": {"lat": 32.7940, "lng": 34.9896},
    "כפר סבא": {"lat": 32.175, "lng": 34.906}
}

business_types = {
    "בתי קפה": "coffee_shop",
    "מסעדות": "restaurant",
    "ברים": "bar",
    "מכוני כושר": "gym",
    "מספרות": "hair_care",
    "בתי מרקחת": "pharmacy"
}

city_name = st.sidebar.selectbox("בחר עיר:", options=list(locations.keys()))
lat = locations[city_name]["lat"]
lng = locations[city_name]["lng"]

selected_label = st.sidebar.selectbox("בחר תחום עסקי:", options=list(business_types.keys()))
place_type = business_types[selected_label]

radius = st.sidebar.slider("רדיוס חיפוש (מטרים):", 500, 5000, 1500)
max_results = st.sidebar.number_input("כמות תוצאות מקסימלית:", 1, 20, 15)

# ------------------------ שליפת הנתונים -----------------------------
url = "https://places.googleapis.com/v1/places:searchNearby"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.priceRange,places.location"
}

payload = {
    "includedTypes": [place_type],
    "maxResultCount": int(max_results),
    "locationRestriction": {
        "circle": {
            "center": {"latitude": lat, "longitude": lng},
            "radius": float(radius)
        }
    }
}

if st.sidebar.button("בצע חיפוש וניתוח SWOT"):
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    places_list = data.get('places', [])

    if not places_list:
        st.error("לא נמצאו תוצאות באזור זה.")
    else:
        # יצירת ה-DataFrame
        df = pd.DataFrame(places_list)

        #ניקוי וסידור הטייפים
        df['name'] = df['displayName'].apply(lambda x: x.get('text') if isinstance(x, dict) else x)
        df['latitude'] = df['location'].apply(lambda x: x.get('latitude') if isinstance(x, dict) else None)
        df['longitude'] = df['location'].apply(lambda x: x.get('longitude') if isinstance(x, dict) else None)
        df = df.rename(columns={'userRatingCount': 'comments_count'})
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df = df.dropna(subset=['rating']) #תוריד לי שורות שאין להן דירוג
        if 'priceRange' in df.columns:
            df['start_price'] = df['priceRange'].apply(
                lambda x: x.get('startPrice', {}).get('units') if isinstance(x, dict) else None)
            df['end_price'] = df['priceRange'].apply(
                lambda x: x.get('endPrice', {}).get('units') if isinstance(x, dict) else None)
        else:
            df['start_price'] = None
            df['end_price'] = None
        df['start_price'] = pd.to_numeric(df['start_price'])
        df['end_price'] = pd.to_numeric(df['end_price'])

        num_competitors = len(df)
        avg_rating = df['rating'].mean()
        median_rating = df['rating'].median()


        st.write(f"##  סקירת שוק: {selected_label} ב{city_name}")

        m1, m2, m3 = st.columns(3)
        m1.metric("מספר מתחרים ברדיוס נבחר", f"{num_competitors}")
        m2.metric("דירוג ממוצע", f"{avg_rating:.2f} ")
        m3.metric("חציון דירוג", f"{median_rating:.1f} ")

        st.write("---")

        col_map, col_data = st.columns([1.2, 1])

        with col_map:
            st.subheader("פריסת מתחרים")
            st.map(df[['latitude', 'longitude']])

        with col_data:
            st.subheader(" פירוט מתחרים")
            st.dataframe(df[['name', 'rating', 'comments_count']], use_container_width=True, height=400)

        st.write("---")
        st.subheader(" ניתוח התפלגות וביצועים")
        gruph1, gruph2 = st.columns(2)

        with gruph1:
            st.write("**דירוג לפי עסק**")
            st.bar_chart(df.set_index('name')['rating'])

        with gruph2:
            st.write("**כמות עסקים לפי רמת דירוג**")
            rating_counts = df['rating'].value_counts().sort_index()
            st.bar_chart(rating_counts)




        gruph3, gruph4 = st.columns(2)
        with gruph3:
            st.write("השפעת המחיר על ציון הביקורת")
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x="end_price", y="rating", ax=ax)
            st.pyplot(fig)


        with gruph4:
            st.write("השפעת המחיר על כמות המדרגים")
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x="end_price", y="comments_count", ax=ax)
            st.pyplot(fig)

        top_filtered = df[df['comments_count'] > 100]
        top_5 = top_filtered.sort_values(by=['rating', 'comments_count'], ascending=False).head(5)
        tabal1 = st.columns(1)

        st.write("חמשת העסקים המובילים בקטגוריה")
        st.dataframe(top_5[['name', 'rating', 'comments_count']])

else:
    st.info("בחר הגדרות ולחץ על הכפתור כדי להתחיל.")

