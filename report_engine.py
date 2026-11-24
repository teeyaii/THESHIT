"""Synthetic-only report tables derived from computed statistics; no empirical claims."""
import hashlib
import json
import math
from pathlib import Path
from docx import Document
from openpyxl import Workbook, load_workbook
from statistical_engine import LABEL

def canonical(report):
    return json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)

def validate(report):
    if report.get("label")!=LABEL:
        raise ValueError("Synthetic report only")
    n,complete,excluded=(report[k] for k in ("n_input","n_complete","n_excluded"))
    if any(type(v) is not int or v<0 for v in (n,complete,excluded)) or complete+excluded!=n:
        raise ValueError("Inconsistent case counts")
    predictors=report["predictors"]
    fields=[report["outcome"],*predictors]
    model=report["model"]
    if (not predictors or len(set(fields))!=len(fields)
            or model.get("independent_ols_hc3_check")!="PASS"):
        raise ValueError("Incomplete computed model or cross-check")
    if [row["variable"] for row in model["coefficients"]]!=["const",*predictors]:
        raise ValueError("Coefficient names inconsistent")
    canonical(report)

def tables(report):
    validate(report)
    model=report["model"]
    fields=[report["outcome"],*report["predictors"]]
    return {
      "Cases":[["Metric","Value"],["Input",report["n_input"]],
               ["Complete",report["n_complete"]],["Excluded",report["n_excluded"]],
               ["Missing policy",report["missing_policy"]]],
      "Descriptive":[["Variable","N","Mean","SD","Min","Max"]]+[
          [k,*[v[f] for f in ("n","mean","sd","min","max")]] for k in fields for v in [report["descriptives"][k]]],
      "Correlation":[["Variable",*fields]]+[
          [k,*[report["correlation"][j][k] for j in fields]]
          for k in fields],
      "Model":[["Metric","Value"],["R squared",model["r_squared"]],
               ["Adjusted R squared",model["adjusted_r_squared"]],["F",model["f"]],
               ["F p",model["f_p"]],["Residual df",model["df_residual"]],
               ["Independent check",model["independent_ols_hc3_check"]]],
      "Coefficients":[["Variable","B","Beta","SE","p","CI lower","CI upper",
                       "HC3 SE","HC3 p","HC3 lower","HC3 upper","VIF"]]+[
          [r["variable"],r["b"],r["beta_standardized"],r["se"],r["p"],*r["ci95"],
           r["hc3_se"],r["hc3_p"],*r["hc3_ci95"],r["vif"]]
          for r in model["coefficients"]],
      "Diagnostics":[["Metric","Value"]]+[[k,report["diagnostics"][k]] for k in sorted(report["diagnostics"])],
      "Missing":[["Variable","Missing count"]]+[[k,report["missing_by_variable"][k]] for k in fields]}

def text_value(value):
    if value is None:
        return "NA"
    if isinstance(value,float):
        return format(value,".8g")
    return str(value)

def md_value(value):
    return text_value(value).replace("\\","\\\\").replace("|","\\|").replace("\r"," ").replace("\n"," ")

def source_hash(report):
    return hashlib.sha256(canonical(report).encode("utf-8")).hexdigest()

def build_report(report,output_dir):
    """New directory only; no user-provided prose, formulas, or empirical claims."""
    table_map=tables(report)
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=False)
    digest=source_hash(report)
    (out/"SYNTHETIC_results.json").write_text(canonical(report),encoding="utf-8")
    workbook=Workbook()
    meta=workbook.active;meta.title="README"
    meta.append([LABEL]);meta.append(["Source SHA256",digest])
    doc=Document()
    doc.add_heading(LABEL,0)
    doc.sections[0].header.paragraphs[0].text=LABEL
    doc.sections[0].footer.paragraphs[0].text=LABEL
    doc.add_paragraph("Computed synthetic results. Not a thesis or field-data report.")
    doc.add_paragraph("Source SHA256: "+digest)
    md=["# "+LABEL,"","Computed synthetic results; no field-data claims.","","Source SHA256: "+digest]
    for name,rows in table_map.items():
        sheet=workbook.create_sheet(name)
        doc.add_heading(name,level=1)
        table=doc.add_table(rows=len(rows),cols=len(rows[0]))
        table.style="Table Grid"
        md.extend(["","## "+name])
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                cell=sheet.cell(i+1,j+1)
                cell.value=value
                if isinstance(value,str):
                    cell.data_type="s"
                table.cell(i,j).text=text_value(value)
            md.append("| "+" | ".join(md_value(v) for v in row)+" |")
            if i==0:
                md.append("| "+" | ".join("---" for _ in row)+" |")
        sheet.freeze_panes="A2"
    doc.add_paragraph("Limitations: "+report["limitations"])
    md.extend(["","Limitations: "+report["limitations"]])
    workbook.save(out/"SYNTHETIC_tables.xlsx")
    doc.save(out/"SYNTHETIC_report.docx")
    (out/"SYNTHETIC_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    return verify_report(out)

def equivalent(expected,actual):
    if isinstance(expected,float):
        return isinstance(actual,(float,int)) and math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-12)
    return expected==actual

def verify_report(output_dir):
    """Reopen exported DOCX/XLSX and compare every table cell to computed JSON."""
    out=Path(output_dir)
    report=json.loads((out/"SYNTHETIC_results.json").read_text(encoding="utf-8"))
    table_map=tables(report)
    digest=source_hash(report)
    workbook=load_workbook(out/"SYNTHETIC_tables.xlsx",read_only=True,data_only=False)
    doc=Document(out/"SYNTHETIC_report.docx")
    count=0
    try:
        if (workbook["README"]["A1"].value!=LABEL or workbook["README"]["B2"].value!=digest
                or doc.paragraphs[0].text!=LABEL
                or doc.paragraphs[2].text!="Source SHA256: "+digest
                or doc.sections[0].header.paragraphs[0].text!=LABEL
                or doc.sections[0].footer.paragraphs[0].text!=LABEL):
            raise ValueError("Source hash or synthetic label mismatch")
        if workbook.sheetnames!=["README",*table_map] or len(doc.tables)!=len(table_map):
            raise ValueError("Missing or unexpected tables")
        for (name,expected),word in zip(table_map.items(),doc.tables):
            actual=list(workbook[name].values)
            if len(actual)!=len(expected) or len(word.rows)!=len(expected):
                raise ValueError("Row count mismatch: "+name)
            for i,row in enumerate(expected):
                if len(actual[i])!=len(row) or len(word.rows[i].cells)!=len(row):
                    raise ValueError("Column count mismatch: "+name)
                for j,value in enumerate(row):
                    if not equivalent(value,actual[i][j]) or word.cell(i,j).text!=text_value(value):
                        raise ValueError("Table value mismatch: "+name)
                    count+=1
    finally:
        workbook.close()
    return {"label":LABEL,"source_sha256":digest,"tables":len(table_map),
            "cells_verified_each_format":count,"structural_qa":"PASS",
            "limitations":"DOCX/XLSX structural QA only; no Word visual, PDF or academic acceptance."}
