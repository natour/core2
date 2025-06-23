import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.colors as mcolors

st.set_page_config(layout="wide")
st.title("Core2 Inverter Log Viewer with Filtering, PDF Export & Interactive Charts")

# Upload log and event CSVs
log_files = st.file_uploader("Upload *_RunRecord_begin*.csv files", type="csv", accept_multiple_files=True)
event_files = st.file_uploader("Upload *_FaultRecord*.csv files", type="csv", accept_multiple_files=True)

if log_files and event_files:
    logs_f, events_f, serials = [], [], []

    columns = ['Total DC Input Power(W)', 'Output Active Power(W)', 'Output Reactive Power(var)',
               'Apparent Power(VA)', 'A-B Line Voltage/Phase A Voltage(V)', 'B-C Line Voltage/Phase B Voltage(V)',
               'C-Line A Voltage/Phase C Voltage(V)', 'Phase A Current(A)', 'Phase B Current(A)',
               'Phase C Current(A)', 'Pf', 'Grid Frequency', 'Internal Temperature (â„–)',
               'Impedance to Earth(kÎ©)', 'PV1 DC voltage(V)', 'PV1 DC current(A)', 'PV2 DC voltage(V)',
               'PV2 DC current(A)', 'PV3 DC voltage(V)', 'PV3 DC current(A)', 'PV4 DC voltage(V)',
               'PV4 DC current(A)', 'PV5 DC voltage(V)', 'PV5 DC current(A)', 'PV6 DC voltage(V)',
               'PV6 DC current(A)', 'PV7 DC voltage(V)', 'PV7 DC current(A)', 'PV8 DC voltage(V)',
               'PV8 DC current(A)', 'PV9 DC voltage(V)', 'PV9 DC current(A)', 'PV10 DC voltage(V)',
               'PV10 DC current(A)', 'PV11 DC voltage(V)', 'PV11 DC current(A)', 'PV12 DC voltage(V)',
               'PV12 DC current(A)', 'Bus Voltage(V)']

    # Load event files
    for ef in event_files:
        df = pd.read_csv(ef, encoding='utf-8')
        df = df.iloc[::-1]
        try:
            df['FullEvent'] = df['Fault Code'].map(str) + "::" + df['Fault Name'].map(str)
        except:
            df['FullEvent'] = df['Fault Code'].map(str)
        df['Time'] = pd.to_datetime(df['Time'], format='%y-%m-%d %H:%M:%S')
        df = df.set_index('Time')
        events_f.append(df)
        serials.append(ef.name.split('_')[1])

    # Load log files
    for lf in log_files:
        df = pd.read_csv(lf, encoding='utf-8')
        df['Time'] = pd.to_datetime(df['Time'], format='%y-%m-%d %H:%M:%S')
        df = df.iloc[::-1].set_index('Time')
        df = df[[col for col in df.columns if col in columns]]
        logs_f.append(df)

    fcolumns = logs_f[0].columns.tolist()
    all_days = sorted(set(logs_f[0].index.to_period('D')))
    selected_day = st.selectbox("Select Day", [str(d) for d in all_days])
    selected_channels = st.multiselect("Select Channels to Plot", fcolumns, default=fcolumns[:5])

    color_map = dict(zip(columns, list(mcolors.TABLEAU_COLORS)))

    # Plotly Interactive Charts
    st.markdown("### Interactive Zoomable Charts")
    for i, serial in enumerate(serials):
        st.subheader(f"Serial: {serial} | Date: {selected_day}")
        log = logs_f[i]
        event = events_f[i]

        toplot = log.loc[str(selected_day)]
        toplotE = event[event.index.to_period('D') == selected_day]

        for col in selected_channels:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=toplot.index, y=toplot[col],
                mode='lines', name=col,
                line=dict(width=2)
            ))

            if not toplotE.empty:
                unique_events = list(toplotE['FullEvent'].unique())
                event_y = [unique_events.index(evt) for evt in toplotE['FullEvent']]

                for evt, x_time in zip(toplotE['FullEvent'], toplotE.index):
                    fig.add_vline(x=x_time, line=dict(color='red', width=1, dash='dash'))
                    fig.add_annotation(
                        x=x_time, y=toplot[col].max(), text=evt,
                        showarrow=True, arrowhead=1, ax=0, ay=-40,
                        font=dict(color='red', size=10),
                        textangle=90
                    )

                
            fig.update_layout(
                title=f"{col} ({serial}) - {selected_day}",
                xaxis_title="Time",
                yaxis_title=col,
                height=500,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

    # PDF Export
    st.markdown("---")
    st.markdown("### Export to PDF")
    if st.button("Generate PDF Report"):
        buffer = BytesIO()
        with PdfPages(buffer) as pdf:
            for i, serial in enumerate(serials):
                log = logs_f[i]
                event = events_f[i]
                toplot = log.loc[str(selected_day)]
                toplotE = event[event.index.to_period('D') == selected_day]

                fig, axarr = plt.subplots(len(selected_channels), 1, figsize=(14, 5 * len(selected_channels)), sharex=True)

                for j, col in enumerate(selected_channels):
                    ax = axarr[j]
                    ax.plot(toplot.index, toplot[col], label=col)
                    ax.set_title(col, y=0.85)
                    ax.grid(True)

                    if not toplotE.empty:
                        unique_events = list(toplotE['FullEvent'].unique())
                        event_colors = dict(zip(unique_events, mcolors.TABLEAU_COLORS))

                        for x, evt in zip(toplotE.index, toplotE['FullEvent']):
                            ax.axvline(x=x, color=event_colors.get(evt, 'red'), linestyle='--', linewidth=1)
                            ax.annotate(evt, xy=(x, toplot[col].max()), xytext=(5, 5),
                                        textcoords='offset points', rotation=90, fontsize=7,
                                        color=event_colors.get(evt, 'red'))

                axarr[-1].xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d %H:%M:%S'))
                for label in axarr[-1].get_xticklabels():
                    label.set_rotation(45)
                    label.set_horizontalalignment("right")

                fig.suptitle(f"{serial} - {selected_day}", fontsize=16, y=0.95)
                fig.subplots_adjust(top=0.91, bottom=0.05, hspace=0.4)
                pdf.savefig(fig)
                plt.close(fig)

        st.success("PDF generated!")
        st.download_button("Download PDF", buffer.getvalue(), "inverter_report.pdf", mime="application/pdf")

else:
    st.info("Please upload both *_RunRecord_begin*.csv and *_FaultRecord*.csv files to begin.")
