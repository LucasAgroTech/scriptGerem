# routes/download_routes.py
import os
from flask import send_file, redirect, url_for, flash, session

def register_download_routes(app):
    """Register all download route handlers for the Flask application"""
    
    @app.route('/download_matches_results')
    def download_matches_results():
        """Download the processed matches results"""
        # Verify user is logged in
        if 'sharepoint_email' not in session:
            return redirect(url_for('login'))
        
        try:
            # Get SharePoint client
            sp_client = app.get_sharepoint_client()
            if not sp_client:
                flash('Error connecting to SharePoint')
                return redirect(url_for('index'))
                
            # Check if the file exists
            result_file = os.path.join(app.config['DOWNLOAD_FOLDER'], 'output_prospeccao.xlsx')
            
            if not os.path.exists(result_file):
                # If file doesn't exist locally, try to download from SharePoint
                try:
                    # Download the file from SharePoint
                    file_content = sp_client.download_file('DWPII/gerem/output_prospeccao.xlsx')
                    
                    # Save locally
                    with open(result_file, 'wb') as f:
                        f.write(file_content)
                except Exception as e:
                    flash(f'No matching results available yet. Please run the matching process first.')
                    return redirect(url_for('index'))
            
            # Log activity
            try:
                current_user = session['sharepoint_email']
                log_details = "Download of matching results"
                sp_client.log_activity(
                    app.config.get('SHAREPOINT_LOGS_PATH', 'General/Lucas Pinheiro/scriptGerem/logs.xlsx'),
                    current_user,
                    "download_matches_results",
                    log_details
                )
            except Exception as log_error:
                print(f"Error logging download activity: {str(log_error)}")
            
            # Send the file for download
            return send_file(
                result_file,
                as_attachment=True,
                download_name="matching_results.xlsx"
            )
            
        except Exception as e:
            flash(f'Error processing download: {str(e)}')
            print(f"Detailed error: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/download_comparison_data')
    def download_comparison_data():
        """Download the detailed comparison data"""
        # Verify user is logged in
        if 'sharepoint_email' not in session:
            return redirect(url_for('login'))
        
        try:
            # Get SharePoint client
            sp_client = app.get_sharepoint_client()
            if not sp_client:
                flash('Error connecting to SharePoint')
                return redirect(url_for('index'))
                
            # Check if the file exists
            comparison_file = os.path.join(app.config['DOWNLOAD_FOLDER'], 'comparacao_gerem_prospeccao.xlsx')
            
            if not os.path.exists(comparison_file):
                # If file doesn't exist locally, try to download from SharePoint
                try:
                    # Download the file from SharePoint
                    file_content = sp_client.download_file('DWPII/gerem/comparacao_gerem_prospeccao.xlsx')
                    
                    # Save locally
                    with open(comparison_file, 'wb') as f:
                        f.write(file_content)
                except Exception as e:
                    flash(f'No comparison data available yet. Please run the matching process first.')
                    return redirect(url_for('index'))
            
            # Log activity
            try:
                current_user = session['sharepoint_email']
                log_details = "Download of comparison data"
                sp_client.log_activity(
                    app.config.get('SHAREPOINT_LOGS_PATH', 'General/Lucas Pinheiro/scriptGerem/logs.xlsx'),
                    current_user,
                    "download_comparison_data",
                    log_details
                )
            except Exception as log_error:
                print(f"Error logging download activity: {str(log_error)}")
            
            # Send the file for download
            return send_file(
                comparison_file,
                as_attachment=True,
                download_name="comparison_data.xlsx"
            )
            
        except Exception as e:
            flash(f'Error processing download: {str(e)}')
            print(f"Detailed error: {str(e)}")
            return redirect(url_for('index'))

    return app