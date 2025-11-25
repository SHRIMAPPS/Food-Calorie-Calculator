# app.py
# The code below is correct for running a Flask web server.
# When you execute this file (e.g., using 'python app.py' in the terminal),
# it will start the server and continue running until manually stopped (e.g., with Ctrl+C).
# Access the web interface by opening a browser to http://127.0.0.1:5002.

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os # Import os for checking file existence

app = Flask(__name__)

# --- Data Loading ---
# Load your calorie data, reading only the required columns
file_name = 'Calorie List.csv' # Make sure this matches your uploaded file name
required_columns = ['Food Item', 'Calories in kcal per 100g']
calorie_data = pd.DataFrame() # Initialize empty DataFrame

print(f"Attempting to load data from '{file_name}'...")

if not os.path.exists(file_name):
    print(f"Error: The file '{file_name}' does not exist.")
else:
    try:
        calorie_data = pd.read_csv(file_name, usecols=required_columns)
        calorie_data = calorie_data.rename(columns={
            'Food Item': 'food_item',
            'Calories in kcal per 100g': 'calories_per_100g'
            })
        # Calculate calories per gram only if calories_per_100g column exists
        if 'calories_per_100g' in calorie_data.columns:
             calorie_data['calories_per_g'] = calorie_data['calories_per_100g'] / 100
        print("Calorie data loaded successfully.")
    except KeyError as e:
        calorie_data = pd.DataFrame() # Reset to empty if columns are missing
        print(f"Error: Missing expected column in '{file_name}': {e}.")
        print("Please check that the column names in your CSV are exactly 'Food Item' and 'Calories in kcal per 100g' (case-sensitive).")
    except Exception as e:
        calorie_data = pd.DataFrame() # Reset to empty on other errors
        print(f"An unexpected error occurred during data loading: {e}")

# --- Helper function for meal analysis (adapted from notebook) ---
def analyze_meal_data(meal_items, calorie_data_df):
    """
    Analyzes a list of meal items (food item and quantity) and calculates
    total calories for the meal and summary statistics for the selected
    food items' calorie content per 100g.

    Args:
        meal_items (list): A list of dictionaries, where each dictionary
                           has 'food_item' (str) and 'quantity' (float in grams).
        calorie_data_df (pd.DataFrame): The DataFrame containing calorie data.

    Returns:
        dict: A dictionary containing the calculated statistics.
    """
    if calorie_data_df.empty:
        return {'error': 'Calorie data not loaded.'}

    total_calories = 0
    selected_food_items_list = [] # List to store food items present in the meal for summary stats
    results = {} # Dictionary to store results

    for item in meal_items:
        food_item_name = item.get('food_item')
        quantity_grams = item.get('quantity', 0) # quantity in grams

        if food_item_name and quantity_grams > 0:
            # Find the food item, case-insensitive match
            calorie_row = calorie_data_df[calorie_data_df['food_item'].str.lower() == food_item_name.lower()]

            if not calorie_row.empty:
                # Get calorie per gram for this food item
                # Check if 'calories_per_g' column exists before accessing
                if 'calories_per_g' in calorie_data_df.columns:
                    energy_per_gram = calorie_row['calories_per_g'].iloc[0]
                    # Calculate calories for the given quantity
                    calories = quantity_grams * energy_per_gram
                    total_calories += calories
                    # Add the food item name to the list for summary stats
                    selected_food_items_list.append(food_item_name)
                    # Optional: print detailed calculation on the server side (visible in Render logs or terminal)
                    print(f"Processed: {food_item_name} ({quantity_grams}g)")
                else:
                    print(f"Warning: 'calories_per_g' column not found. Cannot calculate calories for '{food_item_name}'.")
            else:
                print(f"Warning: Food item '{food_item_name}' not found in data.")
        elif food_item_name:
             print(f"Warning: Quantity for '{food_item_name}' is zero or missing. Skipping.")
        else:
            print(f"Warning: Invalid item format: {item}")

    results['total_calories'] = total_calories

    # Calculate summary statistics for the unique food items included in the meal,
    # based on their calories per 100g from the original data.
    unique_selected_food_items = list(set(selected_food_items_list))
    selected_data_for_stats = calorie_data_df[calorie_data_df['food_item'].isin(unique_selected_food_items)]

    if not selected_data_for_stats.empty and 'calories_per_100g' in selected_data_for_stats.columns:
        results['total_calories_in_selected_food_items_per_100g_sum'] = selected_data_for_stats['calories_per_100g'].sum()
        results['average_calories_per_100g'] = selected_data_for_stats['calories_per_100g'].mean()
        results['median_calories_per_100g'] = selected_data_for_stats['calories_per_100g'].median()
        results['min_calories_per_100g'] = selected_data_for_stats['calories_per_100g'].min()
        results['max_calories_per_100g'] = selected_data_for_stats['calories_per_100g'].max()
        # Check if there's more than one item to calculate std deviation
        if len(selected_data_for_stats) > 1:
            results['std_deviation_calories_per_100g'] = selected_data_for_stats['calories_per_100g'].std()
        else:
             results['std_deviation_calories_per_100g'] = None # Std dev is not meaningful for a single item

        n_top_bottom_selected = min(len(selected_data_for_stats), 5)
        results['highest_calorie_foods_in_selection'] = selected_data_for_stats.nlargest(n_top_bottom_selected, 'calories_per_100g')[['food_item', 'calories_per_100g']].to_dict('records')
        results['lowest_calorie_foods_in_selection'] = selected_data_for_stats.nsmallest(n_top_bottom_selected, 'calories_per_100g')[['food_item', 'calories_per_100g']].to_dict('records')
    else:
        # Initialize stats to None/0 if no items were found/selected for stats
        results['total_calories_in_selected_food_items_per_100g_sum'] = 0
        results['average_calories_per_100g'] = None
        results['median_calories_per_100g'] = None
        results['min_calories_per_100g'] = None
        results['max_calories_per_100g'] = None
        results['std_deviation_calories_per_100g'] = None
        results['highest_calorie_foods_in_selection'] = []
        results['lowest_calorie_foods_in_selection'] = []


    return results


# --- Flask Routes ---

@app.route('/')
def index():
    # Pass the list of food items to the template for a dropdown or list
    food_items_list = calorie_data['food_item'].tolist() if not calorie_data.empty else []
    return render_template('index.html', food_items=food_items_list)

@app.route('/analyze', methods=['POST'])
def analyze():
    # This route handles the POST request from the frontend with meal items
    meal_items = request.json.get('meal_items', [])
    analysis_results = analyze_meal_data(meal_items, calorie_data)
    return jsonify(analysis_results)


# This block is for running the app locally during development.
# Render.com uses a different method to start the application (usually gunicorn).
if __name__ == '__main__':
    # In a production environment like Render, debug=False is recommended for security and performance.
    # For local testing, you can use debug=True
    # This command starts the web server and will "hang" the terminal until stopped.
    app.run(debug=True, port=5002)
