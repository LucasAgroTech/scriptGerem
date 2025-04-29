# routes/api_routes.py
import traceback
from flask import jsonify, session, request

def register_api_routes(app):
    """Register all API route handlers for the Flask application"""
    
    @app.route('/api/start_matching_process', methods=['POST'])
    def start_matching_process():
        """API endpoint to start the matching process"""
        # Check if user is logged in
        if 'sharepoint_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            # Get SharePoint client
            sp_client = app.get_sharepoint_client()
            if not sp_client:
                return jsonify({'error': 'Error connecting to SharePoint'}), 500
            
            # Log activity
            current_user = session['sharepoint_email']
            log_details = "Started matching process"
            sp_client.log_activity(
                app.config.get('SHAREPOINT_LOGS_PATH', 'General/Lucas Pinheiro/scriptGerem/logs.xlsx'),
                current_user,
                "start_matching_process",
                log_details
            )
            
            # Create an instance of SharePointMatcher
            from sharepoint_matching import SharePointMatcher
            sharepoint_matcher = SharePointMatcher(app.config)
            
            # Set the SharePoint client for the matcher
            sharepoint_matcher.set_sharepoint_client(sp_client)
            
            # Perform matching process
            sharepoint_file_path = app.config.get('SHAREPOINT_FILE_PATH', 'General/Lucas Pinheiro/scriptGerem/prospec_consolidado.xlsx')
            prospection_file_path = 'DWPII/srinfo/prospeccao_prospeccao.xlsx'
            
            result = sharepoint_matcher.perform_matching(
                sharepoint_file_path=sharepoint_file_path,
                prospection_file_path=prospection_file_path
            )
            
            if not result['success']:
                return jsonify({'error': result['message']}), 500
            
            return jsonify({
                'success': True,
                'message': 'Matching process completed successfully',
                'total_matches': result['total_matches']
            })
        
        except Exception as e:
            print(f"Error processing matching: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
            
    return app