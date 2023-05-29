from flask import Blueprint,render_template, request,send_file,jsonify
from flask_login import login_required
import pandas as pd
from io import BytesIO
from mSite.models import OrderFormat
from mSite import db
from sqlalchemy import text

inventory = Blueprint("inventory",__name__)



@inventory.route("/inventory", methods=['GET', 'POST'])
@login_required
def inventory_handle():
    return render_template('inventory.html')


# 在你的路由或視圖函式中
@inventory.route('/inventory_stat', methods=['GET'])
def get_statistics():
    query = text('''
    select item_description as item,sum(quantity) as quantity   from inventory_details
    where status= '2'
    group by item_description
    order by sum(quantity) desc
    ''')
    result = db.session.execute(query)

    # 將結果轉換為字典列表
    statistics = []
    for row in result:
        statistics.append({'item': row.item, 'quantity': int(row.quantity)})

    # 回傳統計資料給前端
    return jsonify(statistics)