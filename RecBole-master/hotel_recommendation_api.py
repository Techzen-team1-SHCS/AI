#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotel Recommendation API
Load trained DeepFM model and provide recommendations
"""

import os
import glob
import torch
from flask import Flask, jsonify, request
from recbole.utils.case_study import full_sort_topk
from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, init_seed
import numpy as np
import logging

if not hasattr(np, 'long'):
    np.long = np.int64

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
model = None
config = None
dataset = None
model_loaded = False

def load_latest_model():
    """Load the most recent trained model"""
    global model, config, dataset, model_loaded
    
    try:
        # Tìm file model mới nhất
        model_files = glob.glob("saved/DeepFM-*.pth")
        if not model_files:
            logger.error("ERROR: Không tìm thấy model nào trong thư mục saved/")
            return False
        
        latest_model = max(model_files, key=os.path.getctime)
        logger.info(f"Loading model from: {latest_model}")
        
        # Load checkpoint với weights_only=False để tương thích PyTorch 2.6+
        checkpoint = torch.load(latest_model, weights_only=False, map_location='cpu')
        
        # Lấy config từ checkpoint
        config = checkpoint["config"]
        
        # Init seed và logger
        init_seed(config["seed"], config["reproducibility"])
        init_logger(config)
        
        # Create dataset
        dataset = create_dataset(config)
        logger.info(f"Dataset loaded: {dataset}")
        
        # Prepare data (train_data, valid_data, test_data)
        train_data, valid_data, test_data = data_preparation(config, dataset)
        
        # Create model
        init_seed(config["seed"], config["reproducibility"])
        model = get_model(config["model"])(config, train_data._dataset).to(config["device"])
        
        # Load state dict
        model.load_state_dict(checkpoint["state_dict"])
        
        # Load other parameters if exists
        if "other_parameter" in checkpoint:
            model.load_other_parameter(checkpoint.get("other_parameter"))
        
        model_loaded = True
        logger.info("Model loaded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"ERROR loading model: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Hotel recommendation API active"})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_loaded
    })

@app.route('/recommend', methods=['POST'])
def recommend():
    import torch, traceback
    try:
        if not model_loaded or model is None or dataset is None:
            return jsonify({"error": "Model not loaded", "message": "Model or dataset not ready"}), 500

        payload = request.get_json() or {}
        user_ids = payload.get("user_ids", [])
        top_k = int(payload.get("top_k", 10))

        if not isinstance(user_ids, (list, tuple)) or len(user_ids) == 0:
            return jsonify({"error": "Bad request", "message": "user_ids must be a non-empty list"}), 400

        results = {}

        # field names from dataset (safe)
        uid_field = dataset.uid_field   # e.g. 'user_id'
        iid_field = dataset.iid_field   # e.g. 'item_id'

        for uid_token in user_ids:
            try:
                # convert external token -> internal id (int)
                # token2id can accept single token or list depending on RecBole version
                try:
                    uid_idx = dataset.token2id(uid_field, uid_token)
                except TypeError:
                    # fallback if signature different
                    uid_idx = dataset.token2id(uid_field, [uid_token])[0]

                # if token not found, token2id might return None or raise, handle it
                if uid_idx is None:
                    results[uid_token] = []
                    continue

                # make tensor for model (long dtype)
                uid_tensor = torch.tensor([int(uid_idx)], dtype=torch.long).to(model.device)

                # call full_sort_predict with dict keyed by uid_field
                # many RecBole versions accept a dict like {"user_id": uid_tensor}
                scores = model.full_sort_predict({uid_field: uid_tensor})
                # scores shape: (num_items,) or (1, num_items)
                if scores.dim() == 2 and scores.size(0) == 1:
                    scores = scores.squeeze(0)

                # top-k
                k = min(top_k, scores.size(0))
                topk_scores, topk_indices = torch.topk(scores, k)

                # convert indices -> external item tokens
                topk_item_tokens = []
                for idx in topk_indices.tolist():
                    try:
                        token = dataset.id2token(iid_field, idx)
                    except Exception:
                        # fallback: try dataset.id2token(iid_field, [idx])[0]
                        try:
                            token = dataset.id2token(iid_field, [idx])[0]
                        except Exception:
                            token = str(idx)
                    topk_item_tokens.append(token)

                # prepare result entries
                entries = []
                for it_tok, sc in zip(topk_item_tokens, topk_scores.tolist()):
                    entries.append({"item_id": it_tok, "score": float(sc)})
                results[uid_token] = entries

            except Exception as e_uid:
                # per-user fallback: return empty list and log
                traceback.print_exc()
                results[uid_token] = []

        return jsonify({"recommendations": results}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Recommendation failed", "message": str(e)}), 500

@app.route('/predict_single', methods=['POST'])
def predict_single():
    """
    Predict score for a specific user-hotel pair
    
    Request body:
    {
        "user_id": "u1",
        "hotel_id": "h1"
    }
    """
    if not model_loaded:
        return jsonify({
            'error': 'Model not loaded'
        }), 500
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        hotel_id = data.get('hotel_id')
        
        logger.info(f"Prediction request: user_id={user_id}, hotel_id={hotel_id}")
        
        # Convert to internal IDs
        uid = dataset.token2id(dataset.uid_field, [user_id])
        iid = dataset.token2id(dataset.iid_field, [hotel_id])
        
        # Create interaction
        from torch import tensor
        interaction = {
            dataset.uid_field: tensor(uid),
            dataset.iid_field: tensor(iid)
        }
        
        # Predict
        model.eval()
        score = model.predict(interaction)
        
        logger.info(f"Prediction successful: score={float(score[0].item())}")
        return jsonify({
            'success': True,
            'user_id': user_id,
            'hotel_id': hotel_id,
            'score': float(score[0].item())
        })
        
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500

@app.route('/model/info', methods=['GET'])
def model_info():
    """Get information about loaded model"""
    if not model_loaded:
        return jsonify({
            'error': 'Model not loaded'
        }), 500
    
    try:
        return jsonify({
            'success': True,
            'model_name': config['model'] if 'model' in config else 'DeepFM',
            'dataset': config['dataset'] if 'dataset' in config else 'hotel',
            'num_users': getattr(dataset, 'user_num', None),
            'num_items': getattr(dataset, 'item_num', None),
            'device': str(config['device']) if 'device' in config else 'cpu'
        })
    except Exception as e:
        logger.error(f"Error in model_info: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Loading DeepFM Model for Hotel Recommendation...")
    print("=" * 60)
    
    if load_latest_model():
        print("\nStarting Flask API server...")
        print("API endpoints:")
        print("  - GET  /health : Check if model is loaded")
        print("  - GET  /model/info : Get model information")
        print("  - POST /recommend : Get top K recommendations")
        print("  - POST /predict_single : Predict user-hotel score")
        print("\nListening on http://0.0.0.0:5000")
        print("=" * 60)
        print("\n")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("\nERROR: Failed to load model. Please train a model first.")
        print("Run: python run_recbole.py --model=DeepFM --dataset=hotel")
