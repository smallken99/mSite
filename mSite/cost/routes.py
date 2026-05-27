from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from mSite import db
from sqlalchemy import text

cost = Blueprint("cost", __name__)


@cost.route("/cost", methods=['GET'])
@login_required
def cost_handle():
    return render_template('cost.html')


@cost.route('/cost_available_months', methods=['GET'])
@login_required
def get_cost_available_months():
    """回傳最近 12 個有效月份清單（status='2'）"""
    query = text('''
        SELECT DISTINCT `year_month`
        FROM mSite.inventory_details
        WHERE `status` = '2'
        ORDER BY `year_month` DESC
        LIMIT 12
    ''')
    result = db.session.execute(query)
    months = [row[0] for row in result]
    return jsonify(months)


@cost.route('/cost_stat', methods=['POST'])
@login_required
def get_cost_stat():
    """依選定 year_month 回傳成本彙總（金額由大到小）"""
    req_data = request.get_json()
    selected_month = req_data.get('month', '')

    if not selected_month:
        return jsonify([])

    query = text('''
        SELECT
            DR_ACCOUNT_ID                       AS dr_account_id,
            ITEM_DESCRIPTION                    AS item_description,
            ROUND(SUM(DR_AMOUNT), 2)            AS total_amount,
            SUM(QUANTITY)                       AS total_qty,
            ROUND(SUM(DR_AMOUNT)/SUM(QUANTITY), 2) AS unit_cost
        FROM mSite.inventory_details
        WHERE `status` = '2'
          AND `year_month` = :selected_month
        GROUP BY DR_ACCOUNT_ID, ITEM_DESCRIPTION
        ORDER BY SUM(DR_AMOUNT) DESC
    ''')

    result = db.session.execute(query, {'selected_month': selected_month})

    rows = []
    for row in result:
        rows.append({
            'dr_account_id':   row[0],
            'item_description': row[1],
            'total_amount':    float(row[2]) if row[2] is not None else 0,
            'total_qty':       float(row[3]) if row[3] is not None else 0,
            'unit_cost':       float(row[4]) if row[4] is not None else 0,
        })

    return jsonify(rows)
