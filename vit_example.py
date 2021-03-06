import argparse
import cv2
import numpy as np
import torch
from torch._C import _get_warnAlways
from torchvision import models
from torchvision import transforms
from vit_model import vit_large_patch32_224_in21k as create_model
from pytorch_grad_cam import GradCAM, \
                             ScoreCAM, \
                             GradCAMPlusPlus, \
                             AblationCAM, \
                             XGradCAM, \
                             EigenCAM, \
                             EigenGradCAM

from pytorch_grad_cam import GuidedBackpropReLUModel
from pytorch_grad_cam.utils.image import show_cam_on_image, \
                                         deprocess_image, \
                                         preprocess_image


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-cuda', action='store_true', default=True,
                        help='Use NVIDIA GPU acceleration')
    parser.add_argument('--image-path', type=str, default='dataset\\pic10.jpg',
                        help='Input image path')
    parser.add_argument('--aug_smooth', action='store_true',
                        help='Apply test time augmentation to smooth the CAM')
    parser.add_argument('--eigen_smooth', action='store_true',
                        help='Reduce noise by taking the first principle componenet'
                        'of cam_weights*activations')

    parser.add_argument('--method', type=str, default='gradcam',
                        help='Can be gradcam/gradcam++/scorecam/xgradcam/ablationcam')

    args = parser.parse_args()
    args.use_cuda = args.use_cuda and torch.cuda.is_available()
    if args.use_cuda:
        print('Using GPU for acceleration')
    else:
        print('Using CPU for computation')

    return args

def reshape_transform(tensor, height=7, width=7):
    result = tensor[:, 1 :  , :].reshape(tensor.size(0), 
        height, width, tensor.size(2))

    # Bring the channels to the first dimension,
    # like in CNNs.
    result = result.transpose(2, 3).transpose(1, 2)
    return result

if __name__ == '__main__':
    """ python vit_gradcam.py -image-path <path_to_image>
    Example usage of using cam-methods on a VIT network.
        
    """
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    args = get_args()
    methods = \
        {"gradcam": GradCAM, 
         "scorecam": ScoreCAM, 
         "gradcam++": GradCAMPlusPlus,
         "ablationcam": AblationCAM,
         "xgradcam": XGradCAM,
         "eigencam": EigenCAM,
         "eigengradcam": EigenGradCAM}

    if args.method not in list(methods.keys()):
        raise Exception(f"method should be one of {list(methods.keys())}")

    model = create_model(num_classes=2, has_logits=False).to(device)
    # load model weights
    model_weight_path = 'model-vit.pth'
    model.load_state_dict(torch.load(model_weight_path, map_location=device))
    model.eval()
    
    # model = torch.hub.load('facebookresearch/deit:main', 
        #  'deit_tiny_patch16_224', pretrained=True)
    # model.eval()

    if args.use_cuda:
        model = model.cuda()

    target_layer = model.blocks[-1].norm1

    if args.method not in methods:
        raise Exception(f"Method {args.method} not implemented")

    cam = methods[args.method](model=model, 
                               target_layer=target_layer,
                               use_cuda=args.use_cuda,
                               reshape_transform=reshape_transform)

    rgb_img = cv2.imread(args.image_path, 1)[:, :, ::-1]
    rgb_img = cv2.resize(rgb_img, (224, 224))
    rgb_img = np.float32(rgb_img) / 255
    input_tensor = preprocess_image(rgb_img, mean=[0.5, 0.5, 0.5], 
                                             std=[0.5, 0.5, 0.5])
    
    # If None, returns the map for the highest scoring category.
    # Otherwise, targets the requested category.
    target_category = None

    # AblationCAM and ScoreCAM have batched implementations.
    # You can override the internal batch size for faster computation.
    cam.batch_size = 16
    grayscale_cam = cam(input_tensor=input_tensor,
                        target_category=target_category,
                        eigen_smooth=args.eigen_smooth,
                        aug_smooth=args.aug_smooth)

    # Here grayscale_cam has only one image in the batch
    grayscale_cam = grayscale_cam[0, :]
    # cv2.imshow('1',input_tensor)
    # cv2.waitKey(0)
    # cv2.imshow('1',heatmap)
    # cv2.waitKey(0)
    cam_image = show_cam_on_image(rgb_img, grayscale_cam)
    cv2.imwrite('pic1_vit.jpg', cam_image)
    # cv2.imwrite(f'{args.method}_cam.jpg', cam_image)
    print('---------------------------------{}_cam.jpg ?????????----------------------------' .format(args.method))

    # pic4_res????????????????????????vit?????????pic4_cam????????????????????????heat_map??????