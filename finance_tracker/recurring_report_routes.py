"""Recurring HTML/PDF/CSV share one filtered report service."""
import csv
import io
from xml.sax.saxutils import escape
from flask import Blueprint, request, render_template, Response, send_file, abort
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from .recurring_report import recurring_report, export_columns
from .frequencies import FREQUENCY_LABELS


def report_pdf(report, version):
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,title='Recurring Transactions Report',leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=40)
    styles=getSampleStyleSheet(); story=[]
    def p(text,style='BodyText'): return Paragraph(escape(str(text)),styles[style])
    story.extend([p('Recurring Transactions Report','Title'),p('Finance Tracker v'+version),p('Filters: '+(', '.join(f'{k}: {v}' for k,v in report['filters'].items() if v and k not in ('format','share')) or 'All recurring transactions')),Spacer(1,12)])
    for r in report['rows']:
        block=[p(r['description'],'Heading3'),p(f"{r['frequency_label']} - {r['currency']} {r['amount']:.2f} - {r['transaction_type'].title()}"),
            p(f"{r['account']} | {' / '.join(filter(None,[r['parent_category'],r['category']])) or 'Uncategorised'}"),
            p(f"Next payment: {r['next_payment']} | {'Active' if r['active'] else 'Inactive'}")]
        if report['monthly']: block.append(p(f"{r['currency']} {r['monthly']:.2f}/month equivalent"))
        if report['annual']: block.append(p(f"Annual Equivalent: {r['currency']} {r['annual']:.2f}"))
        story.append(KeepTogether(block+[Spacer(1,8)]))
    if not report['rows']: story.append(p('No recurring transactions match these filters.'))
    totals_start=len(story)
    story.append(p('Totals by payment frequency','Heading2'))
    for g in report['groups']: story.append(p(f"{g['frequency']} | {g['type'].title()} | {g['currency']} {g['amount']:.2f}"))
    for kind,totals in report['totals'].items():
        if report['monthly']: story.append(p(f"Monthly Equivalent Total ({kind}): {report['base']} {totals['monthly']:.2f}"))
        if report['annual']: story.append(p(f"Annual Equivalent Total ({kind}): {report['base']} {totals['annual']:.2f}"))
    if report['monthly'] or report['annual']:
        story.extend([Spacer(1,12),p(report['method']),p(f"Equivalent currency: {report['base']}; existing GBP/EUR rate: {report['fx']}")])
    story[totals_start:]=[KeepTogether(story[totals_start:])]
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.drawRightString(A4[0]-40,22,f'Page {doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer);buf.seek(0);return buf


def create_blueprint(db,login_required,get_setting,latest_fx,version):
    bp=Blueprint('recurring_report',__name__)
    @bp.app_template_filter('decimal_money')
    def decimal_money(value): return format(value,'.2f')

    @bp.get('/reports/recurring')
    @login_required
    def report():
        conn=db()
        try:
            try: result=recurring_report(conn,request.args,get_setting('base_currency','GBP'),latest_fx(conn))
            except (ValueError,KeyError): abort(400,'Invalid recurring report filters.')
            fmt=request.args.get('format','html')
            if fmt=='csv':
                output=io.StringIO(newline=''); writer=csv.writer(output); headers,rows=export_columns(result);writer.writerow(headers)
                for row in rows:
                    writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v for v in row])
                writer.writerow([]);writer.writerow(['Frequency','Currency','Type','Payment total'])
                for g in result['groups']:writer.writerow([g['frequency'],g['currency'],g['type'],format(g['amount'],'.2f')])
                for kind,totals in result['totals'].items():
                    if result['monthly']: writer.writerow(['Monthly Equivalent Total',result['base'],kind,format(totals['monthly'],'.2f')])
                    if result['annual']: writer.writerow(['Annual Equivalent Total',result['base'],kind,format(totals['annual'],'.2f')])
                return Response('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="recurring-transactions.csv"'})
            if fmt=='pdf': return send_file(report_pdf(result,version),mimetype='application/pdf',as_attachment=request.args.get('share')!='1',download_name='recurring-transactions.pdf')
            if fmt!='html': abort(400)
            accounts=conn.execute('SELECT id,name FROM accounts ORDER BY name').fetchall()
            categories=conn.execute('SELECT c.id,c.name,p.name parent_name FROM categories c LEFT JOIN categories p ON p.id=c.parent_id ORDER BY COALESCE(p.name,c.name),c.name').fetchall()
            return render_template('recurring_report.html',report=result,accounts=accounts,categories=categories,frequency_labels=FREQUENCY_LABELS)
        finally: conn.close()
    return bp
