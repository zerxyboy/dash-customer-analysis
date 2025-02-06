# 📌 Step 1: Import Required Libraries
import pandas as pd
import numpy as np
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# 📌 Step 2: Load Data
file_path = "Sales_Dec24_2.csv"  # Ensure the file is in the root directory of your repository
data = pd.read_csv(file_path)

# 📌 Step 3: Clean and Standardise Column Names
data.columns = data.columns.str.replace("\n", " ").str.strip().str.replace(" ", "_")
print(f"✅ Cleaned Column Names:\n{list(data.columns)}")

# 📌 Step 4: Verify Columns
required_columns = [
    "Actuals_k_Local_FY25_YTD", "Actuals_k_Local_FY24",
    "Actuals_k_Sqm_FY25_YTD", "Actuals_k_Sqm_FY24",
    "Budget_k_Local_FY25_YTD", "Budget_k_Sqm_FY24",
    "Avg_AV%_FY25", "Avg_GM%_FY25", "Avg_AV%_Budget", "Avg_GM%_Budget"
]
missing_cols = [col for col in required_columns if col not in data.columns]
if missing_cols:
    print(f"❌ Missing Columns: {missing_cols}")
    raise ValueError("Some required columns are missing in the dataset. Please verify the file.")

# 📌 Step 5: Clean and Convert Data
# Define a function to clean numeric columns
def clean_numeric_column(column):
    return (
        column.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(r"[^\d.-]", "", regex=True)  # Remove all non-numeric characters except '.' and '-'
        .replace(["-", "#DIV/0!", "", " "], np.nan)  # Convert invalid entries to NaN
        .astype(float)
    )

# Apply cleaning to numeric columns
numeric_cols = [
    "Actuals_k_Local_FY25_YTD", "Actuals_k_Local_FY24",
    "Actuals_k_Sqm_FY25_YTD", "Actuals_k_Sqm_FY24",
    "Budget_k_Local_FY25_YTD", "Budget_k_Sqm_FY24"
]
for col in numeric_cols:
    data[col] = clean_numeric_column(data[col])

# Clean and convert percentage columns
def clean_percentage_column(column):
    return (
        column.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace(["-", "#DIV/0!", "", " "], np.nan)
        .astype(float)
    )

percentage_cols = ["Avg_AV%_FY25", "Avg_GM%_FY25", "Avg_AV%_Budget", "Avg_GM%_Budget"]
for col in percentage_cols:
    data[col] = clean_percentage_column(data[col])

# 📌 Step 6: Compute Growth Metrics
data["Revenue_Growth_%"] = (
    (data["Actuals_k_Local_FY25_YTD"] - data["Actuals_k_Local_FY24"]) /
    data["Actuals_k_Local_FY24"].replace(0, np.nan)
) * 100

# 📌 Step 7: Cap Revenue Growth and AV%
growth_cap = 100  # Limit to ±100%
av_cap = -5  # Limit minimum AV% to -5%
data["Capped_Revenue_Growth_%"] = np.clip(data["Revenue_Growth_%"], -growth_cap, growth_cap)
data["Capped_AV%"] = np.clip(data["Avg_AV%_FY25"], av_cap, None)

# 📌 Step 8: Generate Bubble Sizes (Scaled by Volume)
min_bubble_size = 10
max_bubble_size = 300
data["Bubble_Size"] = (
    (data["Actuals_k_Sqm_FY25_YTD"] - data["Actuals_k_Sqm_FY25_YTD"].min()) /
    (data["Actuals_k_Sqm_FY25_YTD"].max() - data["Actuals_k_Sqm_FY25_YTD"].min())
) * (max_bubble_size - min_bubble_size) + min_bubble_size

data["Bubble_Size"] = data["Bubble_Size"].fillna(min_bubble_size).clip(lower=min_bubble_size)

# 📌 Step 9: Setup Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Customer Performance Analysis", style={"text-align": "center"}),

    dcc.Graph(id="scatter_plot"),

    html.Div([
        html.Label("Filter by Revenue Growth Range:"),
        dcc.RangeSlider(
            id="growth_range",
            min=-100, max=100, step=5,
            marks={-100: "-100%", 0: "0%", 100: "100%"},
            value=[-100, 100]
        )
    ], style={"width": "60%", "margin": "auto"}),

    html.Div([
        html.Label("Filter by AV% Range:"),
        dcc.RangeSlider(
            id="av_range",
            min=-5, max=100, step=5,
            marks={-5: "-5%", 0: "0%", 50: "50%", 100: "100%"},
            value=[-5, 100]
        )
    ], style={"width": "60%", "margin": "auto"})
])

# 📌 Step 10: Callback for Interactive Plot
@app.callback(
    Output("scatter_plot", "figure"),
    [Input("growth_range", "value"),
     Input("av_range", "value")]
)
def update_chart(growth_range, av_range):
    filtered_data = data[
        (data["Capped_Revenue_Growth_%"] >= growth_range[0]) &
        (data["Capped_Revenue_Growth_%"] <= growth_range[1]) &
        (data["Capped_AV%"] >= av_range[0]) &
        (data["Capped_AV%"] <= av_range[1])
    ]

    fig = px.scatter(
        filtered_data,
        x="Capped_AV%",
        y="Capped_Revenue_Growth_%",
        size="Bubble_Size",
        color=np.where(filtered_data["Capped_AV%"] < 0, "Below 0% AV", "Above 0% AV"),
        hover_name="BillToName",
        hover_data={
            "Capped_AV%": True,
            "Capped_Revenue_Growth_%": True,
            "Actuals_k_Local_FY25_YTD": True,
            "Actuals_k_Sqm_FY25_YTD": True,
        },
        title="Customer Performance Relative to AV% and Revenue Growth",
        labels={"Capped_AV%": "AV% FY25 (Capped at -5%)",
                "Capped_Revenue_Growth_%": "Revenue Growth (Capped at ±100%)"},
        category_orders={"color": ["Above 0% AV", "Below 0% AV"]},
        color_discrete_map={"Above 0% AV": "green", "Below 0% AV": "red"},
    )

    # Add reference lines
    fig.add_shape(
        type="line", x0=-5, x1=100, y0=0, y1=0,
        line=dict(color="black", width=2, dash="dash")
    )
    fig.add_shape(
        type="line", x0=46, x1=46, y0=-100, y1=100,
        line=dict(color="blue", width=2, dash="dot")
    )

    # Add quadrant labels
    fig.add_annotation(x=75, y=80, text="⭐ Star", showarrow=False, font=dict(size=14, color="black"))
    fig.add_annotation(x=-2, y=80, text="❓ Question Mark", showarrow=False, font=dict(size=14, color="black"))
    fig.add_annotation(x=75, y=-80, text="💰 Cash Cow", showarrow=False, font=dict(size=14, color="black"))
    fig.add_annotation(x=-2, y=-80, text="🐶 Dog", showarrow=False, font=dict(size=14, color="black"))

    return fig

# 📌 Step 11: Run the App
if __name__ == "__main__":
    app.run_server(debug=True)
