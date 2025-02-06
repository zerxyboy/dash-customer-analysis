import dash
from dash import dcc, html
import pandas as pd
import plotly.express as px

# ✅ Load & clean data
file_path = "Sales_Dec24_2.csv"
data = pd.read_csv(file_path)

# ✅ Dash app setup
app = dash.Dash(__name__)

# ✅ Define layout
app.layout = html.Div([
    dcc.Graph(
        id="scatter-plot",
        figure=px.scatter(
            data,
            x="Avg_AV%_FY25",
            y="Revenue_Growth_%",
            size="Actuals_k_Sqm_FY25_YTD",
            hover_name="BillToName",
            title="Customer Performance",
            labels={"Avg_AV%_FY25": "AV% FY25", "Revenue_Growth_%": "Revenue Growth (%)"},
        )
    )
])

# ✅ Fix for Gunicorn
server = app.server  # Make server visible for deployment

# ✅ Run app locally
if __name__ == "__main__":
    app.run_server(debug=True)
