import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, ConcatDataset
import time
import deepdish as dd
from networks import ClassifierLogits, Classifier
import torch.distributions as tdist
import os
import argparse
import numpy as np
import copy
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def main(args):
    torch.manual_seed(args.seed)
    if not os.path.exists(args.res_dir):
        os.makedirs(args.res_dir, exist_ok=True)

    if not os.path.exists(args.model_dir):
        os.makedirs(args.model_dir, exist_ok=True)

    if not os.path.exists(args.id_dir):
        os.makedirs(args.id_dir, exist_ok=True)


    data1 = dd.io.load(os.path.join(args.vec_dir,'NYU_correlation_matrix.h5'))
    data2 = dd.io.load(os.path.join(args.vec_dir,'UM_correlation_matrix.h5'))
    data3 = dd.io.load(os.path.join(args.vec_dir,'USM_correlation_matrix.h5'))
    data4 = dd.io.load(os.path.join(args.vec_dir,'UCLA_correlation_matrix.h5'))

    x1 = torch.from_numpy(data1['data']).float()
    y1 = torch.from_numpy(data1['label']).long()
    x2 = torch.from_numpy(data2['data']).float()
    y2 = torch.from_numpy(data2['label']).long()
    x3 = torch.from_numpy(data3['data']).float()
    y3 = torch.from_numpy(data3['label']).long()
    x4 = torch.from_numpy(data4['data']).float()
    y4 = torch.from_numpy(data4['label']).long()

    if args.overlap:
        idNYU = dd.io.load('./idx/NYU_sub_overlap.h5')
        idUM = dd.io.load('./idx/UM_sub_overlap.h5')
        idUSM = dd.io.load('./idx/USM_sub_overlap.h5')
        idUCLA = dd.io.load('./idx/UCLA_sub_overlap.h5')
    else:
        idNYU = dd.io.load('./idx/NYU_sub.h5')
        idUM = dd.io.load('./idx/UM_sub.h5')
        idUSM = dd.io.load('./idx/USM_sub.h5')
        idUCLA = dd.io.load('./idx/UCLA_sub.h5')

    if args.split==0:
        tr1 = idNYU['1']+idNYU['2']+idNYU['3']+idNYU['4']
        tr2 = idUM['1']+idUM['2']+idUM['3']+idUM['4']
        tr3 = idUSM['1']+idUSM['2']+idUSM['3']+idUSM['4']
        tr4 = idUCLA['1']+idUCLA['2']+idUCLA['3']+idUCLA['4']
        te1=  idNYU['0']
        te2 = idUM['0']
        te3=  idUSM['0']
        te4 = idUCLA['0']
    elif args.split==1:
        tr1 = idNYU['0']+idNYU['2']+idNYU['3']+idNYU['4']
        tr2 = idUM['0']+idUM['2']+idUM['3']+idUM['4']
        tr3 = idUSM['0']+idUSM['2']+idUSM['3']+idUSM['4']
        tr4 = idUCLA['0']+idUCLA['2']+idUCLA['3']+idUCLA['4']
        te1=  idNYU['1']
        te2 = idUM['1']
        te3=  idUSM['1']
        te4 = idUCLA['1']
    elif args.split==2:
        tr1 = idNYU['0']+idNYU['1']+idNYU['3']+idNYU['4']
        tr2 = idUM['0']+idUM['1']+idUM['3']+idUM['4']
        tr3 = idUSM['0']+idUSM['1']+idUSM['3']+idUSM['4']
        tr4 = idUCLA['0']+idUCLA['1']+idUCLA['3']+idUCLA['4']
        te1=  idNYU['2']
        te2 = idUM['2']
        te3=  idUSM['2']
        te4 = idUCLA['2']
    elif args.split==3:
        tr1 = idNYU['0']+idNYU['1']+idNYU['2']+idNYU['4']
        tr2 = idUM['0']+idUM['1']+idUM['2']+idUM['4']
        tr3 = idUSM['0']+idUSM['1']+idUSM['2']+idUSM['4']
        tr4 = idUCLA['0']+idUCLA['1']+idUCLA['2']+idUCLA['4']
        te1=  idNYU['3']
        te2 = idUM['3']
        te3=  idUSM['3']
        te4 = idUCLA['3']
    elif args.split==4:
        tr1 = idNYU['0']+idNYU['1']+idNYU['2']+idNYU['3']
        tr2 = idUM['0']+idUM['1']+idUM['2']+idUM['3']
        tr3 = idUSM['0']+idUSM['1']+idUSM['2']+idUSM['3']
        tr4 = idUCLA['0']+idUCLA['1']+idUCLA['2']+idUCLA['3']
        te1=  idNYU['4']
        te2 = idUM['4']
        te3=  idUSM['4']
        te4 = idUCLA['4']

    x1_train = x1[tr1]
    y1_train = y1[tr1]
    x2_train = x2[tr2]
    y2_train = y2[tr2]
    x3_train = x3[tr3]
    y3_train = y3[tr3]
    x4_train = x4[tr4]
    y4_train = y4[tr4]

    x1_test = x1[te1]
    y1_test = y1[te1]
    x2_test = x2[te2]
    y2_test = y2[te2]
    x3_test = x3[te3]
    y3_test = y3[te3]
    x4_test = x4[te4]
    y4_test = y4[te4]


    if args.sepnorm:
        # 标准化的方法？
        mean = x1_train.mean(0, keepdim=True)
        dev = x1_train.std(0, keepdim=True)
        x1_train = (x1_train - mean) / dev
        x1_test = (x1_test - mean) / dev

        mean = x2_train.mean(0, keepdim=True)
        dev = x2_train.std(0, keepdim=True)
        x2_train = (x2_train - mean) / dev
        x2_test = (x2_test - mean) / dev

        mean = x3_train.mean(0, keepdim=True)
        dev = x3_train.std(0, keepdim=True)
        x3_train = (x3_train - mean) / dev
        x3_test = (x3_test - mean) / dev

        mean = x4_train.mean(0, keepdim=True)
        dev = x4_train.std(0, keepdim=True)
        x4_train = (x4_train - mean) / dev
        x4_test = (x4_test - mean) / dev
    else:
        mean = torch.cat((x1_train,x2_train,x3_train,x4_train),0).mean(0, keepdim=True)
        dev = torch.cat((x1_train,x2_train,x3_train,x4_train),0).std(0, keepdim=True)
        x1_train = (x1_train - mean) / dev
        x1_test = (x1_test - mean) / dev
        x2_train = (x2_train - mean) / dev
        x2_test = (x2_test - mean) / dev
        x3_train = (x3_train - mean) / dev
        x3_test = (x3_test - mean) / dev
        x4_train = (x4_train - mean) / dev
        x4_test = (x4_test - mean) / dev

    train1 = TensorDataset(x1_train, y1_train)
    train_loader1 = DataLoader(train1, batch_size=len(train1)//args.nsteps, shuffle=True)
    train2 = TensorDataset(x2_train, y2_train)
    train_loader2 = DataLoader(train2, batch_size=len(train2)//args.nsteps, shuffle=True)
    train3 = TensorDataset(x3_train, y3_train)
    train_loader3 = DataLoader(train3, batch_size=len(train3)//args.nsteps, shuffle=True)
    train4 = TensorDataset(x4_train, y4_train)
    train_loader4 = DataLoader(train4, batch_size=len(train4)//args.nsteps, shuffle=True)
    train_loaders = [train_loader1, train_loader2, train_loader3, train_loader4]
    data_inters = [iter(train_loader1),iter(train_loader2),iter(train_loader3),iter(train_loader4)]

    test1 = TensorDataset(x1_test, y1_test)
    test2 = TensorDataset(x2_test, y2_test)
    test3 = TensorDataset(x3_test, y3_test)
    test4 = TensorDataset(x4_test, y4_test)
    test_loader1 = DataLoader(test1, batch_size=args.test_batch_size1, shuffle=False)
    test_loader2 = DataLoader(test2, batch_size=args.test_batch_size2, shuffle=False)
    test_loader3 = DataLoader(test3, batch_size=args.test_batch_size3, shuffle=False)
    test_loader4 = DataLoader(test4, batch_size=args.test_batch_size4, shuffle=False)
    tbs= [args.test_batch_size1, args.test_batch_size2, args.test_batch_size3, args.test_batch_size4]
    test_loaders = [test_loader1,test_loader2,test_loader3,test_loader4]



    # federated set up
    # model1 = MoE(6105,args.feddim,2).to(device)
    # model2 = MoE(6105,args.feddim,2).to(device)
    # model3 = MoE(6105,args.feddim,2).to(device)
    # model4 = MoE(6105,args.feddim,2).to(device)
    # 这个难道是


    # models = [model1, model2, model3, model4]
    # optimizers = [optimizer1, optimizer2, optimizer3, optimizer4]
    # 服务端的全局模型
    model = ClassifierLogits(6105,args.feddim,2).to(device)
    print('Global Model:', model)

    # local set up, does not communicate with federated model
    model_local1 = ClassifierLogits(6105,args.dim,2).to(device)
    model_local2 = ClassifierLogits(6105,args.dim,2).to(device)
    model_local3 = ClassifierLogits(6105,args.dim,2).to(device)
    model_local4 = ClassifierLogits(6105,args.dim,2).to(device)
    # 备份的模型，teacher 的输出基于这些模型
    model_backup1 = ClassifierLogits(6105, args.dim, 2).to(device)
    model_backup2 = ClassifierLogits(6105, args.dim, 2).to(device)
    model_backup3 = ClassifierLogits(6105, args.dim, 2).to(device)
    model_backup4 = ClassifierLogits(6105, args.dim, 2).to(device)

    for bak, curr in zip((model_backup1, model_backup2, model_backup3, model_backup4), (model_local1, model_local2, model_local3, model_local4)):
        bak.load_state_dict(curr.state_dict())
    model_backups = [model_backup1, model_backup2, model_backup3, model_backup4]
    optimizer_local1 = optim.Adam(model_local1.parameters(), lr=args.llr, weight_decay=5e-2)
    optimizer_local2 = optim.Adam(model_local2.parameters(), lr=args.llr, weight_decay=5e-2)
    optimizer_local3 = optim.Adam(model_local3.parameters(), lr=args.llr, weight_decay=5e-2)
    optimizer_local4 = optim.Adam(model_local4.parameters(), lr=args.llr, weight_decay=5e-2)
    models_local = [model_local1, model_local2, model_local3, model_local4]
    optimizers_local = [optimizer_local1, optimizer_local2, optimizer_local3, optimizer_local4]

    nnloss = nn.NLLLoss()  # 输入的数据集经过了 log_softmax
    klloss = nn.KLDivLoss(reduction='mean')
    sites = ['NYU', 'UM', 'USM', 'UCLA']
    def train(epoch):
        pace = args.pace
        for i in range(4):
            # 每个客户端的模型进行训练
            # models_local[i].train()
            if epoch <= 50 and epoch % 20 == 0:
                for param_group1 in optimizers_local[i].param_groups:
                    param_group1['lr'] = 0.5 * param_group1['lr']
            elif epoch > 50 and epoch % 20 == 0:
                for param_group1 in optimizers_local[i].param_groups:
                    param_group1['lr'] = 0.5 * param_group1['lr']


        #define weights
        w = dict()
        denominator = np.sum(np.array(tbs))
        for i in range(4):
            # 估计是平均的聚合直接乘以 1/4
            w[i] = 0.25 #tbs[i]/denominator
        loss_all = dict()
        loss_lc = dict()
        loss_kl = dict()
        num_data = dict()
        for i in range(4):
            loss_all[i] = 0
            loss_lc[i] = 0
            num_data[i] = 0
            loss_kl[i] = 0
        count = 0
        for t in range(args.nsteps):
            for i in range(4):
                # 清空梯度信息
                optimizers_local[i].zero_grad()
                # 读取数据，这个似乎是从迭代器里取得
                try:
                    a, b = next(data_inters[i])
                except StopIteration:
                    data_inters[i] = iter(train_loaders[i])
                    a, b = next(data_inters[i])
                num_data[i] += b.size(0)
                a = a.to(device)
                b = b.to(device)
                dists = []
                models_local[i].train()
                with torch.no_grad():
                    for j in range(4):
                        # 这个部分训练得到其他的模型对于当前客户端的数据的输出
                        if j == i:
                            continue
                        model_backups[j].eval()
                        client_j_dis = model_backups[j](a)
                        dists.append(client_j_dis)
                # 计算平均的 logits
                dist_avg = torch.zeros_like(dists[-1])
                for dist in dists:
                    dist_avg += dist
                dist_avg /= len(dists)
                # 计算两个损失函数
                log_soft_out = F.log_softmax(models_local[i](a), dim=1)
                cls_loss = nnloss(log_soft_out, b)
                # kl loss
                kl_loss = klloss(log_soft_out, F.softmax(dist_avg, dim=1))
                total_loss = cls_loss + kl_loss
                # total_loss = kl_loss
                total_loss.backward()
                # 记录损失函数等信息
                num_batch = b.size(0)
                loss_kl[i] += kl_loss.item() * num_batch
                loss_lc[i] += cls_loss.item() * num_batch
                # loss_lc[i] += 0.0
                loss_all[i] += total_loss.item() * num_batch
                # 这个是更新的客户端本地的参数
                optimizers_local[i].step()
            # 所有的机构训练完毕
            for bak, curr in zip(model_backups, models_local):
                bak.load_state_dict(curr.state_dict())

            count += 1

            # 在内部循环中已经默认使用了对方的参数
            # if count % pace == 0 or t == args.nsteps-1:
            #     with torch.no_grad():
            #         # 复制参数到全局模型中
            #         for key in model.classifier.state_dict().keys():
            #             if models_local[0].state_dict()[key].dtype == torch.int64:
            #                 # TODO 复制一些比如 BN 中 num_batch_tracked 之类的参数，反正各个local模型中都是一样的
            #                 model.classifier.state_dict()[key].data.copy_(models_local[0].state_dict()[key])
            #             else:
            #                 temp = torch.zeros_like(model.classifier.state_dict()[key])
            #                 # add noise
            #                 for s in range(4):
            #                     # nn = tdist.Normal(torch.tensor([0.0]), args.noise*torch.std(models[s].classifier.state_dict()[key].detach().cpu()))
            #                     # noise = nn.sample(models[i].classifier.state_dict()[key].size()).squeeze()
            #                     # noise = noise.to(device)
            #                     # temp += w[s] * (models[s].classifier.state_dict()[key] + noise)
            #                     temp += w[s] * models_local[s].state_dict()[key]
            #                 #updata global model
            #                 model.classifier.state_dict()[key].data.copy_(temp)
            #                 # only classifier get updated
            #                 for s in range(4):
            #                     models_local[s].state_dict()[key].data.copy_(model.state_dict()[key])

        return loss_all[0] / num_data[0], loss_all[1] / num_data[1],loss_all[2] / num_data[2],loss_all[3] / num_data[3], \
               loss_lc[0] / num_data[0],loss_lc[1] / num_data[1], loss_lc[2] / num_data[2], loss_lc[3] / num_data[3], \
               loss_kl[0] / num_data[0], loss_kl[1] / num_data[1], loss_kl[2] / num_data[2], loss_kl[3] / num_data[3]


    def test(federated_model,dataloader,site_name, train = True):
        federated_model.eval()
        test_loss = 0
        correct = 0
        for data, target in dataloader:
            data = data.to(device)
            target = target.to(device)
            output = federated_model(data)
            output = F.log_softmax(output, dim=1)
            test_loss += nnloss(output, target).item()*target.size(0)
            pred = output.data.max(1)[1]
            correct += pred.eq(target.view(-1)).sum().item()

        test_loss /= len(dataloader.dataset)
        correct /= len(dataloader.dataset)
        print(f"Site {site_name}")
        if train:
            print('\tTrain set local: Average loss: {:.4f}, Average acc: {:.4f}'.format(test_loss,correct))
        else:
            print('\tTest set local: Average loss: {:.4f}, Average acc: {:.4f}'.format(test_loss, correct))
        return test_loss, correct

    def testfed(federated_model,local_model,dataloader,train=True):
        federated_model= federated_model.to(device)
        local_model = local_model.to(device)
        federated_model.eval()
        local_model.eval()
        test_loss = 0
        correct = 0
        outputs = []
        preds = []
        targets = []
        gates = []
        for data, target in dataloader:
            data = data.to(device)
            targets.append(target[0].detach().numpy())
            target = target.to(device)
            local_output = local_model(data)
            output, a = federated_model(data,local_output)
            outputs.append(output.detach().cpu().numpy())
            gates.append(a.detach().cpu().numpy())
            test_loss += nnloss(output, target).item()*target.size(0)
            pred = output.data.max(1)[1]
            preds.append(pred.detach().cpu().numpy())
            correct += pred.eq(target.view(-1)).sum().item()

        test_loss /= len(dataloader.dataset)
        correct /= len(dataloader.dataset)
        if train:
            print('Train set fed: Average loss: {:.4f}, Average acc: {:.4f}'.format(test_loss,correct))
        else:
            print('Test set fed: Average loss: {:.4f}, Average acc: {:.4f}'.format(test_loss, correct))
        return test_loss, correct, targets, outputs, preds,gates


    best_acc = [0,0,0,0]
    best_epoch = [0,0,0,0]

    for epoch in range(args.epochs):
        start_time = time.time()
        print(f"Epoch Number {epoch + 1}")
        l1,l2,l3,l4,lc1,lc2,lc3,lc4, kl1, kl2, kl3, kl4 = train(epoch)
        print("===========================")
        print("L1: {:.7f}, L2: {:.7f}, L3: {:.7f}, L4: {:.7f}, Lc1: {:.7f}, Lc2: {:.7f}, Lc3: {:.7f}, Lc4: {:.7f} "
              "kl1: {:.7f}, kl2: {:.7f}, kl3: {:.7f}, kl4: {:.7f}".format(l1,l2,l3,l4,lc1,lc2,lc3,lc4,
                                                                          kl1, kl2, kl3, kl4))

        #local model performance
        print("***Local***")
        te_accs = []
        for i in range(4):
            train_loss, train_acc = test(models_local[i], train_loaders[i], site_name=sites[i], train=True)
            test_loss, test_acc = test(models_local[i], test_loaders[i], site_name=sites[i], train=False)
            te_accs.append(test_acc)


        #fed model performance
        # 这个是评估全局模型的在各个客户端上的性能
        # print("***Federated***")
        # for i in range(4):
        #     test(model, train_loaders[i],train = True)
        #     test(model,test_loaders[i], train = False)
        # moe model performance
        # print("***MOE***")
        # te_accs= list()
        # targets = list()
        # outputs = list()
        # preds = list()
        # gates = list()
        # for i in range(4):
        #     testfed(models[i],models_local[i], train_loaders[i],train = True)
        #     _, te_acc, tar,out,pre, gate = testfed(models[i],models_local[i], test_loaders[i],train = False)
        #     te_accs.append(te_acc)
        #     targets.append(tar)
        #     outputs.append(out)
        #     preds.append(pre)
        #     gates.append(gate)

        for i in range(4):
            if te_accs[i] >best_acc[i]:
                best_acc[i] = te_accs[i]
                best_epoch[i] = epoch

        total_time = time.time() - start_time
        print('Communication time over the network', round(total_time, 2), 's\n')
    model_wts = copy.deepcopy(model.state_dict())
    torch.save(model_wts, os.path.join(args.model_dir, str(args.split) +'.pth'))
    # dd.io.save(os.path.join(args.res_dir, 'NYU_' + str(args.split) + '.h5'),
    #             {'outputs': outputs[0], 'preds': preds[0], 'targets': targets[0], 'gates':gates[0]})
    # dd.io.save(os.path.join(args.res_dir, 'UM_' + str(args.split) + '.h5'),
    #             {'outputs': outputs[1], 'preds': preds[1], 'targets': targets[1], 'gates':gates[1]})
    # dd.io.save(os.path.join(args.res_dir, 'USM_' + str(args.split) + '.h5'),
    #             {'outputs': outputs[2], 'preds': preds[2], 'targets': targets[2], 'gates':gates[2]})
    # dd.io.save(os.path.join(args.res_dir, 'UCLA_' + str(args.split) + '.h5'),
    #             {'outputs': outputs[3], 'preds': preds[3], 'targets': targets[3], 'gates':gates[3]})
    for i in range(4):
        print('Site: ', sites[i] , ' Best Acc:',best_acc[i], 'Best Epoch:', best_epoch[i])

    print('split:', args.split,'   noise:', args.noise, '   pace:', args.pace)

#==========================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # specify for dataset site
    parser.add_argument('--split', type=int, default=0, help='select 0-4 fold')
    # do not need to change
    parser.add_argument('--pace', type=int, default=20, help='communication pace')
    parser.add_argument('--noise', type=float, default=0.01, help='noise level')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--lr1', type=float, default=1e-5)
    parser.add_argument('--lr2', type=float, default=1e-5)
    parser.add_argument('--lr3', type=float, default=1e-5)
    parser.add_argument('--lr4', type=float, default=1e-5)
    parser.add_argument('--llr', type=float, default=1e-5, help='local model learning rate')
    parser.add_argument('--clip', type=float, default=2.0, help='gradient clip')
    parser.add_argument('--dim', type=int, default=8,help='hidden dim of MLP')
    parser.add_argument('--feddim', type=int, default=16, help='hidden dim of FedMLP')
    parser.add_argument('--nsteps', type=int, default=60, help='training steps/epoach')
    parser.add_argument('-tbs1', '--test_batch_size1', type=int, default=145, help='NYU test batch size')
    parser.add_argument('-tbs2', '--test_batch_size2', type=int, default=265, help='UM test batch size')
    parser.add_argument('-tbs3', '--test_batch_size3', type=int, default=205, help='USM test batch size')
    parser.add_argument('-tbs4', '--test_batch_size4', type=int, default=85, help='UCLA test batch size')
    parser.add_argument('--overlap', type=bool, default=True, help='augmentation method')
    parser.add_argument('--sepnorm', type=bool, default=True, help='normalization method')
    parser.add_argument('--id_dir', type=str, default='./idx')
    parser.add_argument('--res_dir', type=str, default='./result/feddistill_overlap')
    parser.add_argument('--vec_dir', type=str, default='./data')
    parser.add_argument('--model_dir', type=str, default='./model/feddistill_overlap')
    args = parser.parse_args()
    assert args.split in [0,1,2,3,4]
    main(args)
