import webbrowser
import os
import json
from jinja2 import Environment, FileSystemLoader
from bot.config import settings

from bot.utils import logger

async def generate_statistics_html_page():
    with open("statistics.json", 'r') as file:
        statistics = json.load(file)

    statistics_list = [
        {
            "wallet": statistic_item["wallet"],
            "referralCounts": statistic_item["referrals"],
            "referralLink": statistic_item["referralLink"],
            "balance": statistic_item["balance"],
            "name": statistic_item["name"],
            "userId": statistic_item["userId"],
        }
        for statistic_item in statistics.values()
    ]

    total_balance = sum(item['balance'] for item in statistics_list)

    html_template = """
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paws Statistics</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
        <style>
            /* Base Styles */
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                font-family: 'Roboto', sans-serif;
                background-color: #fafafa;
                color: #333;
                display: flex;
                flex-direction: column;
                align-items: center;
                align-items: center;
                min-height: 100vh;
            }

            .header {
                position: sticky;
                top: 0;
                width: 100vw;
                padding: 10px 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2rem;
                color: #fff;
                background: #3f51b5;
            }

            .header a {
                margin-right: 15px;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .header a:hover {
                transform: rotate(90deg);
            }

            .header i {
                font-size: 3.5rem;
                color: #333;
            }

            .header span {
                font-weight: bold;
            }

            h1 {
                text-align: center;
                margin-top: 30px;
                margin-bottom: 30px;
                font-size: 2.5rem;
                color: #3f51b5;
            }

            h2 {
                text-align: center;
                margin-bottom: 30px;
                font-size: 1.5rem;
                color: #3f51b5;
            }

            .container {
                background-color: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                width: 100%;
                max-width: 95%;
                overflow-x: auto;
                margin-bottom: 30px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                border-radius: 8px;
                overflow: hidden;
            }

            th,
            td {
                padding: 16px;
                text-align: left;
                font-size: 0.8rem;
                border-bottom: 1px solid #ddd;
            }

            th {
                background-color: #3f51b5;
                color: white;
                font-weight: 500;
            }

            tr:nth-child(even) {
                background-color: #f4f4f4;
            }

            tr:hover {
                background-color: #e8e8e8;
            }

            td a {
                color: #3f51b5;
                text-decoration: none;
            }

            td a:hover {
                text-decoration: underline;
            }

            .balance {
                font-weight: 600;
                color: #4caf50;
            }

            .no-data {
                text-align: center;
                font-style: italic;
                color: #aaa;
            }


        /* Pagination styles */
        .pagination {
            display: flex;
            justify-content: center;
            margin-top: 20px;
        }

        .pagination button {
            background-color: #3f51b5;
            color: white;
            border: none;
            padding: 10px 15px;
            margin: 0 5px;
            cursor: pointer;
            border-radius: 5px;
            font-size: 1rem;
        }

        .pagination button:hover {
            background-color: #303f9f;
        }

        .pagination button:disabled {
            background-color: #ddd;
            cursor: not-allowed;
        }

            /* Responsive Adjustments */
            @media (max-width: 768px) {
                h1 {
                    font-size: 2rem;
                }

                th,
                td {
                    padding: 12px;
                    font-size: 0.9rem;
                }

                .container {
                    padding: 15px;
                }
            }

            @media (max-width: 480px) {
                h1 {
                    font-size: 1.8rem;
                }

                th,
                td {
                    padding: 10px;
                    font-size: 0.85rem;
                }

                .container {
                    padding: 10px;
                }
            }
        </style>
    </head>

    <body>
        <div class="header">
            <a href="https://github.com/YarmolenkoD/paws" target="_blank">
                <i class="fab fa-github"></i>
            </a>
            <span>Developed by YarmolenkoD</span>
        </div>

        <div>
            <h1>🐾 Paws Statistics 🐾</h1>
            <h2>🐾 Total Balance: {{ '{:,.3f}'.format(total_balance) }} 🐾</h2>
        </div>
        <div class="container">
            <table id="userTable">
                <tr>
                    <th>№</th>
                    <th>Name</th>
                    <th>Id</th>
                    <th>Wallet</th>
                    <th>Referral Counts</th>
                    <th>Referral Link</th>
                    <th>Balance</th>
                </tr>
                {% if statistics|length == 0 %}
                <tr>
                    <td colspan="6" class="no-data">No user data available</td>
                </tr>
                {% else %}
                {% for item in statistics %}
                <tr class="userRow">
                    <td>{{ loop.index }}</td>
                    <td>{{ item.name }}</td>
                    <td>{{ item.userId }}</td>
                    <td>{{ item.wallet }}</td>
                    <td>{{ item.referralCounts }}</td>
                    <td><a href="{{ item.referralLink }}" target="_blank">{{ item.referralLink }}</a></td>
                    <td class="balance">${{ item.balance }}</td>
                </tr>
                {% endfor %}
                {% endif %}
            </table>

            {% if statistics|length >= 15 %}
            <!-- Pagination controls -->
            <div class="pagination" id="paginationControls">
                <button id="prevPage" onclick="changePage(-1)" disabled>Previous</button>
                <button id="nextPage" onclick="changePage(1)">Next</button>
            </div>
            {% endif %}
        </div>
        <script>
             // Pagination script
             let currentPage = 1;
             const rowsPerPage = 10;
             const table = document.getElementById('userTable');
             const rows = Array.from(table.getElementsByClassName('userRow'));
             const totalPages = Math.ceil(rows.length / rowsPerPage);

             function changePage(direction) {
                 currentPage += direction;
                 currentPage = Math.max(1, Math.min(currentPage, totalPages));
                 updateTable();
             }

             function updateTable() {
                 const startIndex = (currentPage - 1) * rowsPerPage;
                 const endIndex = startIndex + rowsPerPage;

                 // Show only the rows for the current page
                 rows.forEach((row, index) => {
                     if (index >= startIndex && index < endIndex) {
                         row.style.display = '';
                     } else {
                         row.style.display = 'none';
                     }
                 });

                 // Update pagination buttons
                 document.getElementById('prevPage').disabled = currentPage === 1;
                 document.getElementById('nextPage').disabled = currentPage === totalPages;
             }

             // Initial table update
             updateTable();
         </script>
    </body>

    </html>
    """

    # Initialize Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'))
    template = env.from_string(html_template)

    # Render the HTML with user data
    html_content = template.render(statistics=statistics_list, total_balance=total_balance)

    with open("statistics.html", "w") as file:
        file.write(html_content)
        logger.success(f"Statistics page successfully generated to statistics.html file ✅")


    try:
        file_path = os.path.abspath("statistics.html")
        logger.info(f"Opening statistics in browser 🌐")
        webbrowser.open(f"file://{file_path}")
    except Exception as error:
        logger.warning(f"Can't open statistics page in browser, but you can find stats in statistics.json file.")